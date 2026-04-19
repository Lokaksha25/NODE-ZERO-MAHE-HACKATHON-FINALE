from __future__ import annotations

import json
import logging
import math
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


LOGGER = logging.getLogger("build_corridor_dataset")

ROOT = Path(__file__).resolve().parents[2]
CACHE_DIR = ROOT / "data" / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

ROUTES_CACHE_PATH = CACHE_DIR / "corridor_routes_scored.json"
TOWERS_CACHE_PATH = CACHE_DIR / "opencellid_towers.json"

# Default corridor is intentionally short to keep API usage low.
# Override any of these with environment variables if needed.
ORIGIN = (10.7522, 59.9139)  # Oslo
DESTINATION = (10.2045, 59.7439)  # Drammen (short corridor)
CORRIDOR_NAME = "oslo-drammen"

SAMPLE_INTERVAL_M = float(os.getenv("CORRIDOR_SAMPLE_INTERVAL_M", "9000"))
MAX_TILE_CENTERS = int(os.getenv("CORRIDOR_MAX_TILE_CENTERS", "18"))
TILE_DELTA = float(os.getenv("CORRIDOR_TILE_DELTA", "0.009"))
SPLIT_MAX_DEPTH = int(os.getenv("CORRIDOR_SPLIT_MAX_DEPTH", "1"))

# Internal app operator ids are jio/airtel. For this corridor:
# - jio maps to Telenor-like MCC/MNCs
# - airtel maps to Telia-like MCC/MNCs
OPERATOR_MNC_MAP = {
    "jio": {(242, 1), (242, 14), (242, 23)},
    "airtel": {(242, 2), (242, 5), (242, 25)},
}

RADIO_WEIGHTS = {
    "NR": 1.15,
    "LTE": 1.0,
    "UMTS": 0.62,
    "GSM": 0.30,
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


@dataclass
class FetchStats:
    requests: int = 0
    split_tiles: int = 0
    http_errors: int = 0
    payload_errors: int = 0


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


def fetch_json(url: str, params: dict[str, Any], timeout: int = 45) -> dict[str, Any]:
    query = urlencode(params)
    request = Request(
        f"{url}?{query}",
        headers={
            "User-Agent": "node-zero-hackathon/0.2",
            "Accept": "application/json",
        },
    )
    with urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def percentile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    idx = (len(ordered) - 1) * q
    lo = int(math.floor(idx))
    hi = int(math.ceil(idx))
    if lo == hi:
        return ordered[lo]
    frac = idx - lo
    return ordered[lo] * (1 - frac) + ordered[hi] * frac


def fetch_osrm_routes() -> list[dict[str, Any]]:
    base = "https://router.project-osrm.org/route/v1/driving"
    waypoint_sets = [
        [],
        [(10.5100, 59.8700)],  # slight detour for an alternative
        [(10.4300, 59.9600)],  # northern detour for 3rd viable route
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
            key = (
                f"{len(geometry)}:"
                f"{geometry[0][0]:.5f}:{geometry[0][1]:.5f}:"
                f"{geometry[-1][0]:.5f}:{geometry[-1][1]:.5f}"
            )
            if key in seen_keys:
                continue
            seen_keys.add(key)
            unique.append(route)

    unique.sort(key=lambda route: route.get("duration", float("inf")))
    selected = unique[:3]
    LOGGER.info(
        "OSRM returned %d unique routes; selected %d", len(unique), len(selected)
    )
    for idx, route in enumerate(selected, start=1):
        LOGGER.info(
            "Route %d: distance=%.2f km duration=%d min",
            idx,
            route.get("distance", 0.0) / 1000.0,
            int(round(route.get("duration", 0.0) / 60.0)),
        )
    return selected


def haversine_meters(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    radius = 6371000
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (
        math.sin(d_lat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(d_lon / 2) ** 2
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


def segmentize_geometry(
    geometry: list[list[float]], segment_length_m: float = 120.0
) -> list[dict[str, float]]:
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

            seg_start = interpolate_point(
                start[0], start[1], end[0], end[1], ratio_start
            )
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
        if (
            haversine_meters(tail["end_lon"], tail["end_lat"], tail_end[0], tail_end[1])
            > 40
        ):
            segments.append(
                {
                    "start_lon": tail["end_lon"],
                    "start_lat": tail["end_lat"],
                    "end_lon": tail_end[0],
                    "end_lat": tail_end[1],
                }
            )

    return segments


def sample_tile_centers(
    routes: list[dict[str, Any]], interval_m: float = SAMPLE_INTERVAL_M
) -> list[tuple[float, float]]:
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
                lon, lat = interpolate_point(
                    p1[0], p1[1], p2[0], p2[1], max(0.0, min(1.0, ratio))
                )
                key = f"{lat:.4f}:{lon:.4f}"
                if key not in seen:
                    seen.add(key)
                    centers.append((lat, lon))
                next_mark += interval_m
            acc += step

    if len(centers) > MAX_TILE_CENTERS:
        step = max(1, math.ceil(len(centers) / MAX_TILE_CENTERS))
        centers = centers[::step][:MAX_TILE_CENTERS]

    return centers


def _fetch_bbox_cells(
    api_key: str,
    lat: float,
    lon: float,
    delta: float,
    stats: FetchStats,
) -> list[dict[str, Any]]:
    params = {
        "key": api_key,
        "BBOX": f"{lat - delta:.6f},{lon - delta:.6f},{lat + delta:.6f},{lon + delta:.6f}",
        "format": "json",
    }
    stats.requests += 1
    payload = fetch_json("https://opencellid.org/cell/getInArea", params)
    if payload.get("error") and payload.get("code") != 1:
        stats.payload_errors += 1
        LOGGER.debug(
            "OpenCellID payload error for BBOX=%s code=%s error=%s",
            params["BBOX"],
            payload.get("code"),
            payload.get("error"),
        )
        return []
    return payload.get("cells", [])


def _fetch_bbox_recursive(
    api_key: str,
    lat: float,
    lon: float,
    delta: float,
    depth: int = 0,
    max_depth: int = SPLIT_MAX_DEPTH,
    stats: FetchStats | None = None,
) -> list[dict[str, Any]]:
    if stats is None:
        stats = FetchStats()

    try:
        cells = _fetch_bbox_cells(api_key, lat, lon, delta, stats)
    except (HTTPError, URLError):
        stats.http_errors += 1
        LOGGER.debug("HTTP/URL error while fetching tile lat=%.6f lon=%.6f", lat, lon)
        return []

    if len(cells) < 50 or depth >= max_depth or delta <= 0.002:
        return cells

    stats.split_tiles += 1
    LOGGER.debug(
        "Tile split triggered at depth=%d lat=%.6f lon=%.6f delta=%.6f",
        depth,
        lat,
        lon,
        delta,
    )

    results: list[dict[str, Any]] = []
    half = delta / 2
    for lat_shift in (-half, half):
        for lon_shift in (-half, half):
            results.extend(
                _fetch_bbox_recursive(
                    api_key=api_key,
                    lat=lat + lat_shift,
                    lon=lon + lon_shift,
                    delta=half,
                    depth=depth + 1,
                    max_depth=max_depth,
                    stats=stats,
                )
            )
    return results


def fetch_opencellid_towers(api_key: str, routes: list[dict[str, Any]]) -> list[Tower]:
    centers = sample_tile_centers(routes)
    delta = TILE_DELTA
    stats = FetchStats()

    towers: dict[tuple[Any, ...], Tower] = {}
    start_time = time.time()

    LOGGER.info(
        "Sampling %d OpenCellID tiles | interval=%.0fm | max_tiles=%d | split_depth=%d | delta=%.4f",
        len(centers),
        SAMPLE_INTERVAL_M,
        MAX_TILE_CENTERS,
        SPLIT_MAX_DEPTH,
        TILE_DELTA,
    )

    for index, (lat, lon) in enumerate(centers, start=1):
        rows = _fetch_bbox_recursive(api_key, lat, lon, delta, stats=stats)

        for row in rows:
            try:
                tower = Tower(
                    lat=float(row["lat"]),
                    lon=float(row["lon"]),
                    mcc=int(row["mcc"]),
                    mnc=int(row["mnc"]),
                    lac=int(row.get("lac", 0) or 0),
                    cellid=int(row.get("cellid", 0) or 0),
                    radio=str(row.get("radio", "GSM") or "GSM").upper(),
                    range_m=max(
                        200.0, min(float(row.get("range", 1000) or 1000), 5000.0)
                    ),
                    samples=int(row.get("samples", 0) or 0),
                )
            except (TypeError, ValueError, KeyError):
                continue

            key = (
                tower.mcc,
                tower.mnc,
                tower.lac,
                tower.cellid,
                tower.lat,
                tower.lon,
                tower.radio,
            )
            if key not in towers:
                towers[key] = tower

        if index == 1 or index % 10 == 0 or index == len(centers):
            elapsed = time.time() - start_time
            LOGGER.info(
                "Tile %d/%d processed | rows=%d | unique_towers=%d | requests=%d | elapsed=%.1fs",
                index,
                len(centers),
                len(rows),
                len(towers),
                stats.requests,
                elapsed,
            )

        time.sleep(0.05)

    LOGGER.info(
        "OpenCellID fetch finished: towers=%d requests=%d split_tiles=%d http_errors=%d payload_errors=%d",
        len(towers),
        stats.requests,
        stats.split_tiles,
        stats.http_errors,
        stats.payload_errors,
    )
    return list(towers.values())


def operator_for_tower(tower: Tower) -> str | None:
    key = (tower.mcc, tower.mnc)
    for operator, mapped in OPERATOR_MNC_MAP.items():
        if key in mapped:
            return operator
    return None


def _tower_quality_weight(tower: Tower) -> float:
    sample_weight = (
        0.35
        if tower.samples <= 1
        else min(1.0, math.log1p(tower.samples) / math.log(40))
    )
    range_weight = 0.78 if abs(tower.range_m - 1000.0) < 1e-6 else 1.0
    return sample_weight * range_weight


def score_segment_for_operator(
    midpoint_lon: float,
    midpoint_lat: float,
    towers: list[Tower],
    operator: str,
) -> float:
    mapped_candidates: list[tuple[float, float]] = []
    generic_candidates: list[tuple[float, float]] = []

    for tower in towers:
        distance = haversine_meters(midpoint_lon, midpoint_lat, tower.lon, tower.lat)
        if distance > 3500:
            continue

        radio_weight = RADIO_WEIGHTS.get(tower.radio.upper(), 0.22)
        quality = _tower_quality_weight(tower)
        distance_decay = math.exp(-distance / max(350.0, tower.range_m * 0.9))
        contribution = radio_weight * quality * distance_decay

        matched_operator = operator_for_tower(tower)
        if matched_operator == operator:
            mapped_candidates.append((distance, contribution))
        elif matched_operator is None:
            generic_candidates.append((distance, contribution * 0.38))

    mapped_candidates.sort(key=lambda item: item[0])
    generic_candidates.sort(key=lambda item: item[0])

    mapped_score = sum(score for _, score in mapped_candidates[:8])
    generic_score = sum(score for _, score in generic_candidates[:5])

    if mapped_score == 0:
        return generic_score
    return mapped_score + generic_score * 0.2


def normalize_scores(raw_scores: list[float], floor: float = 18.0) -> list[float]:
    if not raw_scores:
        return []

    non_zero = [value for value in raw_scores if value > 0]
    if not non_zero:
        return [floor * 0.6 for _ in raw_scores]

    p10 = percentile(non_zero, 0.10)
    p90 = percentile(non_zero, 0.90)

    if p90 <= p10:
        max_value = max(non_zero)
        if max_value <= 0:
            return [floor * 0.6 for _ in raw_scores]
        return [
            round(floor + (value / max_value) * (100.0 - floor), 2)
            if value > 0
            else round(floor * 0.6, 2)
            for value in raw_scores
        ]

    normalized: list[float] = []
    for value in raw_scores:
        if value <= 0:
            normalized.append(round(floor * 0.6, 2))
            continue

        ratio = (value - p10) / (p90 - p10)
        ratio = min(1.0, max(0.0, ratio))
        boosted = ratio**0.72
        normalized.append(round(floor + boosted * (100.0 - floor), 2))

    return normalized


def build_scored_routes(
    routes: list[dict[str, Any]], towers: list[Tower]
) -> list[dict[str, Any]]:
    scored: list[dict[str, Any]] = []
    route_intermediate: list[dict[str, Any]] = []
    all_jio_raw: list[float] = []
    all_airtel_raw: list[float] = []

    for route in routes:
        geometry = route["geometry"]["coordinates"]
        segments = segmentize_geometry(geometry)

        jio_raw: list[float] = []
        airtel_raw: list[float] = []

        for segment in segments:
            midpoint_lon = (segment["start_lon"] + segment["end_lon"]) / 2
            midpoint_lat = (segment["start_lat"] + segment["end_lat"]) / 2
            jio_raw.append(
                score_segment_for_operator(midpoint_lon, midpoint_lat, towers, "jio")
            )
            airtel_raw.append(
                score_segment_for_operator(midpoint_lon, midpoint_lat, towers, "airtel")
            )

        all_jio_raw.extend(jio_raw)
        all_airtel_raw.extend(airtel_raw)

        route_intermediate.append(
            {
                "route": route,
                "segments": segments,
                "jio_raw": jio_raw,
                "airtel_raw": airtel_raw,
            }
        )

    # Normalize against corridor-wide distributions, not per-route maxima.
    jio_all_norm = normalize_scores(all_jio_raw, floor=18.0)
    airtel_all_norm = normalize_scores(all_airtel_raw, floor=18.0)

    jio_cursor = 0
    airtel_cursor = 0

    for idx, item in enumerate(route_intermediate):
        route = item["route"]
        segments = item["segments"]
        jio_len = len(item["jio_raw"])
        airtel_len = len(item["airtel_raw"])

        jio_norm = jio_all_norm[jio_cursor : jio_cursor + jio_len]
        airtel_norm = airtel_all_norm[airtel_cursor : airtel_cursor + airtel_len]

        jio_cursor += jio_len
        airtel_cursor += airtel_len

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
                        "airtel": airtel_norm[seg_idx]
                        if seg_idx < len(airtel_norm)
                        else 0.0,
                    },
                }
            )

        scored.append(
            {
                "route_id": f"osrm_route_{idx + 1}",
                "label": f"Route {chr(65 + idx)}",
                "distance_km": round(route["distance"] / 1000.0, 2),
                "eta_minutes": int(round(route["duration"] / 60.0)),
                "geometry": route["geometry"]["coordinates"],
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
    log_level = os.getenv("CORRIDOR_BUILD_LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format="%(asctime)s | %(levelname)s | %(message)s",
    )

    env = load_env(ROOT / ".env")
    api_key = env.get("OPENCELLID_API_KEY") or os.getenv("OPENCELLID_API_KEY")
    if not api_key:
        raise RuntimeError("OPENCELLID_API_KEY is required in .env or environment")

    LOGGER.info("Starting corridor dataset build for %s", CORRIDOR_NAME)
    LOGGER.info(
        "Origin=(%.4f, %.4f) Destination=(%.4f, %.4f)",
        ORIGIN[1],
        ORIGIN[0],
        DESTINATION[1],
        DESTINATION[0],
    )
    LOGGER.info(
        "Budget knobs: interval=%.0fm max_tiles=%d split_depth=%d delta=%.4f",
        SAMPLE_INTERVAL_M,
        MAX_TILE_CENTERS,
        SPLIT_MAX_DEPTH,
        TILE_DELTA,
    )

    routes = fetch_osrm_routes()
    if not routes:
        raise RuntimeError("OSRM did not return any routes")

    towers = fetch_opencellid_towers(api_key, routes)
    if len(towers) < 50:
        raise RuntimeError(
            "OpenCellID returned too few towers. "
            "Likely API quota exceeded or upstream throttling. "
            "Aborting cache write to avoid replacing good data."
        )

    scored_routes = build_scored_routes(routes, towers)
    LOGGER.info("Scored %d routes with %d towers", len(scored_routes), len(towers))

    now = int(time.time())

    ROUTES_CACHE_PATH.write_text(
        json.dumps(
            {
                "source": "osrm+opencellid",
                "corridor": CORRIDOR_NAME,
                "generated_at": now,
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
                "corridor": CORRIDOR_NAME,
                "generated_at": now,
                "tower_count": len(towers),
                "towers": serialize_towers(towers),
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    print(f"Wrote {ROUTES_CACHE_PATH}")
    print(f"Wrote {TOWERS_CACHE_PATH}")
    print(
        f"Corridor: {CORRIDOR_NAME} | Routes: {len(scored_routes)} | Towers: {len(towers)}"
    )
    LOGGER.info("Dataset build completed successfully")


if __name__ == "__main__":
    main()
