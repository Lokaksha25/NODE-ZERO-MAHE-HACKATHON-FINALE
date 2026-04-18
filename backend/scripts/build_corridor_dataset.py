from __future__ import annotations

import json
import math
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
CACHE_DIR = ROOT / "data" / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

ROUTES_CACHE_PATH = CACHE_DIR / "corridor_routes_scored.json"
TOWERS_CACHE_PATH = CACHE_DIR / "opencellid_towers.json"

ORIGIN = (77.6173, 12.9352)  # Koramangala
DESTINATION = (76.6558, 12.3052)  # Mysuru Palace

OPERATOR_MNC_MAP = {
    "jio": {(405, 86), (405, 87), (405, 861)},
    "airtel": {(404, 10), (404, 49), (404, 45)},
}

RADIO_WEIGHTS = {
    "LTE": 1.0,
    "UMTS": 0.6,
    "GSM": 0.35,
}


@dataclass(frozen=True)
class Tower:
    lat: float
    lon: float
    mcc: int
    mnc: int
    lac: int
    cellid: int
    radio: str
    range_m: float
    samples: int


def load_env(path: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    if not path.exists():
        return env
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        env[key.strip()] = value.strip()
    return env


def fetch_json(url: str, params: dict[str, Any], timeout: int = 40) -> dict[str, Any]:
    query = urlencode(params)
    request = Request(
        f"{url}?{query}",
        headers={
            "User-Agent": "node-zero-hackathon/0.1",
            "Accept": "application/json",
        },
    )
    with urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_osrm_routes() -> list[dict[str, Any]]:
    base = "https://router.project-osrm.org/route/v1/driving"
    waypoint_sets = [
        [],
        [(77.3000, 12.6300)],
        [(76.9800, 12.4300)],
    ]

    unique: list[dict[str, Any]] = []
    seen_keys: set[str] = set()

    for vias in waypoint_sets:
        points = [ORIGIN, *vias, DESTINATION]
        coords = ";".join(f"{lon},{lat}" for lon, lat in points)
        payload = fetch_json(
            f"{base}/{coords}",
            {
                "alternatives": "true",
                "overview": "full",
                "geometries": "geojson",
                "steps": "false",
            },
        )

        for route in payload.get("routes", []):
            geometry = route["geometry"]["coordinates"]
            if len(geometry) < 2:
                continue
            key = f"{len(geometry)}:{geometry[0][0]:.5f}:{geometry[0][1]:.5f}:{geometry[-1][0]:.5f}:{geometry[-1][1]:.5f}"
            if key in seen_keys:
                continue
            seen_keys.add(key)
            unique.append(route)

    unique.sort(key=lambda route: route.get("duration", float("inf")))
    return unique[:3]


def haversine_meters(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    radius = 6371000
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (
        math.sin(d_lat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(d_lon / 2) ** 2
    )
    return 2 * radius * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def interpolate_point(
    lon1: float,
    lat1: float,
    lon2: float,
    lat2: float,
    ratio: float,
) -> tuple[float, float]:
    return (lon1 + (lon2 - lon1) * ratio, lat1 + (lat2 - lat1) * ratio)


def segmentize_geometry(geometry: list[list[float]], segment_length_m: float = 100.0) -> list[dict[str, float]]:
    segments: list[dict[str, float]] = []

    carry_start = (geometry[0][0], geometry[0][1])
    carry_remaining = segment_length_m

    for idx in range(1, len(geometry)):
        end = (geometry[idx][0], geometry[idx][1])
        start = carry_start
        distance = haversine_meters(start[0], start[1], end[0], end[1])
        if distance <= 0:
            continue

        progress = 0.0
        while progress < distance:
            step = min(carry_remaining, distance - progress)
            ratio_start = progress / distance
            ratio_end = (progress + step) / distance

            seg_start = interpolate_point(start[0], start[1], end[0], end[1], ratio_start)
            seg_end = interpolate_point(start[0], start[1], end[0], end[1], ratio_end)

            carry_remaining -= step
            progress += step

            if carry_remaining <= 1e-6:
                segments.append(
                    {
                        "start_lon": seg_start[0],
                        "start_lat": seg_start[1],
                        "end_lon": seg_end[0],
                        "end_lat": seg_end[1],
                    }
                )
                carry_remaining = segment_length_m

        carry_start = end

    if segments:
        tail_end = (geometry[-1][0], geometry[-1][1])
        tail = segments[-1]
        if haversine_meters(tail["end_lon"], tail["end_lat"], tail_end[0], tail_end[1]) > 25:
            segments.append(
                {
                    "start_lon": tail["end_lon"],
                    "start_lat": tail["end_lat"],
                    "end_lon": tail_end[0],
                    "end_lat": tail_end[1],
                }
            )

    return segments


def sample_tile_centers(routes: list[dict[str, Any]], interval_m: float = 5000) -> list[tuple[float, float]]:
    centers: list[tuple[float, float]] = []
    seen: set[str] = set()

    for route in routes:
        coords = route["geometry"]["coordinates"]
        if len(coords) < 2:
            continue

        acc = 0.0
        next_mark = 0.0
        for idx in range(1, len(coords)):
            p1 = coords[idx - 1]
            p2 = coords[idx]
            step = haversine_meters(p1[0], p1[1], p2[0], p2[1])
            while next_mark <= acc + step:
                ratio = 0 if step == 0 else (next_mark - acc) / step
                lon, lat = interpolate_point(p1[0], p1[1], p2[0], p2[1], max(0.0, min(1.0, ratio)))
                key = f"{lat:.4f}:{lon:.4f}"
                if key not in seen:
                    seen.add(key)
                    centers.append((lat, lon))
                next_mark += interval_m
            acc += step

    return centers


def fetch_opencellid_towers(api_key: str, routes: list[dict[str, Any]]) -> list[Tower]:
    centers = sample_tile_centers(routes)
    delta = 0.0075

    towers: dict[tuple[Any, ...], Tower] = {}

    for lat, lon in centers:
        params = {
            "key": api_key,
            "BBOX": f"{lat - delta:.6f},{lon - delta:.6f},{lat + delta:.6f},{lon + delta:.6f}",
            "format": "json",
        }
        try:
            payload = fetch_json("https://opencellid.org/cell/getInArea", params)
        except (HTTPError, URLError):
            time.sleep(0.2)
            continue
        if payload.get("error") and payload.get("code") != 1:
            continue

        for row in payload.get("cells", []):
            try:
                tower = Tower(
                    lat=float(row["lat"]),
                    lon=float(row["lon"]),
                    mcc=int(row["mcc"]),
                    mnc=int(row["mnc"]),
                    lac=int(row.get("lac", 0) or 0),
                    cellid=int(row.get("cellid", 0) or 0),
                    radio=str(row.get("radio", "GSM") or "GSM").upper(),
                    range_m=max(200.0, min(float(row.get("range", 1000) or 1000), 5000.0)),
                    samples=int(row.get("samples", 0) or 0),
                )
            except (TypeError, ValueError, KeyError):
                continue

            key = (tower.mcc, tower.mnc, tower.lac, tower.cellid, tower.lat, tower.lon, tower.radio)
            if key not in towers:
                towers[key] = tower
        time.sleep(0.1)

    return list(towers.values())


def operator_for_tower(tower: Tower) -> str | None:
    key = (tower.mcc, tower.mnc)
    for operator, mapped in OPERATOR_MNC_MAP.items():
        if key in mapped:
            return operator
    return None


def score_segment_for_operator(
    midpoint_lon: float,
    midpoint_lat: float,
    towers: list[Tower],
    operator: str,
) -> float:
    contribution = 0.0
    for tower in towers:
        if operator_for_tower(tower) != operator:
            continue

        distance = haversine_meters(midpoint_lon, midpoint_lat, tower.lon, tower.lat)
        if distance > 2000:
            continue

        radio_weight = RADIO_WEIGHTS.get(tower.radio.upper(), 0.25)
        confidence = min(1.0, math.log1p(max(0, tower.samples)) / math.log(10))
        confidence = max(0.2, confidence)
        distance_decay = math.exp(-distance / max(250.0, tower.range_m))

        contribution += radio_weight * confidence * distance_decay
    return contribution


def normalize_scores(raw_scores: list[float]) -> list[float]:
    if not raw_scores:
        return []
    max_score = max(raw_scores)
    if max_score <= 0:
        return [0.0 for _ in raw_scores]
    return [min(100.0, round((value / max_score) * 100.0, 2)) for value in raw_scores]


def build_scored_routes(routes: list[dict[str, Any]], towers: list[Tower]) -> list[dict[str, Any]]:
    scored: list[dict[str, Any]] = []

    for idx, route in enumerate(routes):
        geometry = route["geometry"]["coordinates"]
        segments = segmentize_geometry(geometry)

        jio_raw: list[float] = []
        airtel_raw: list[float] = []
        for segment in segments:
            midpoint_lon = (segment["start_lon"] + segment["end_lon"]) / 2
            midpoint_lat = (segment["start_lat"] + segment["end_lat"]) / 2
            jio_raw.append(score_segment_for_operator(midpoint_lon, midpoint_lat, towers, "jio"))
            airtel_raw.append(score_segment_for_operator(midpoint_lon, midpoint_lat, towers, "airtel"))

        jio_norm = normalize_scores(jio_raw)
        airtel_norm = normalize_scores(airtel_raw)

        route_segments = []
        for seg_idx, segment in enumerate(segments):
            route_segments.append(
                {
                    "start_lon": segment["start_lon"],
                    "start_lat": segment["start_lat"],
                    "end_lon": segment["end_lon"],
                    "end_lat": segment["end_lat"],
                    "scores": {
                        "jio": jio_norm[seg_idx] if seg_idx < len(jio_norm) else 0.0,
                        "airtel": airtel_norm[seg_idx] if seg_idx < len(airtel_norm) else 0.0,
                    },
                }
            )

        scored.append(
            {
                "route_id": f"osrm_route_{idx + 1}",
                "label": f"Route {chr(65 + idx)}",
                "distance_km": round(route["distance"] / 1000.0, 2),
                "eta_minutes": int(round(route["duration"] / 60.0)),
                "geometry": geometry,
                "segments": route_segments,
            }
        )

    return scored


def serialize_towers(towers: list[Tower]) -> list[dict[str, Any]]:
    payload: list[dict[str, Any]] = []
    for tower in towers:
        payload.append(
            {
                "lat": tower.lat,
                "lon": tower.lon,
                "mcc": tower.mcc,
                "mnc": tower.mnc,
                "lac": tower.lac,
                "cellid": tower.cellid,
                "radio": tower.radio,
                "range": tower.range_m,
                "samples": tower.samples,
                "operator": operator_for_tower(tower),
            }
        )
    return payload


def main() -> None:
    env = load_env(ROOT / ".env")
    api_key = env.get("OPENCELLID_API_KEY") or os.getenv("OPENCELLID_API_KEY")
    if not api_key:
        raise RuntimeError("OPENCELLID_API_KEY is required in .env or environment")

    routes = fetch_osrm_routes()
    if not routes:
        raise RuntimeError("OSRM did not return any routes")

    towers = fetch_opencellid_towers(api_key, routes)
    scored_routes = build_scored_routes(routes, towers)

    ROUTES_CACHE_PATH.write_text(
        json.dumps(
            {
                "source": "osrm+opencellid",
                "generated_at": int(time.time()),
                "route_count": len(scored_routes),
                "tower_count": len(towers),
                "routes": scored_routes,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    TOWERS_CACHE_PATH.write_text(
        json.dumps(
            {
                "source": "opencellid",
                "generated_at": int(time.time()),
                "tower_count": len(towers),
                "towers": serialize_towers(towers),
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    print(f"Wrote {ROUTES_CACHE_PATH}")
    print(f"Wrote {TOWERS_CACHE_PATH}")
    print(f"Routes: {len(scored_routes)}, Towers: {len(towers)}")


if __name__ == "__main__":
    main()
