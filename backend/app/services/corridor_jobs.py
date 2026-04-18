from __future__ import annotations

import hashlib
import json
import math
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import mapbox_vector_tile


ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
CACHE_DIR = DATA_DIR / "cache"
CORRIDOR_CACHE_DIR = CACHE_DIR / "corridors"
CORRIDOR_CACHE_DIR.mkdir(parents=True, exist_ok=True)

JOB_DIR = CACHE_DIR / "jobs"
JOB_DIR.mkdir(parents=True, exist_ok=True)

TTL_SECONDS = 24 * 60 * 60

OPERATOR_MNC_MAP: dict[str, set[tuple[int, int]]] = {
    "jio": {(242, 1), (242, 14), (242, 23)},
    "airtel": {(242, 2), (242, 5), (242, 25)},
}

RADIO_WEIGHTS = {
    "NR": 1.15,
    "LTE": 1.0,
    "UMTS": 0.62,
    "GSM": 0.30,
}


@dataclass
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


_executor = ThreadPoolExecutor(max_workers=1)
_lock = threading.Lock()
_jobs: dict[str, dict[str, Any]] = {}


def _now() -> int:
    return int(time.time())


def _job_path(job_id: str) -> Path:
    return JOB_DIR / f"{job_id}.json"


def _corridor_dir(corridor_id: str) -> Path:
    return CORRIDOR_CACHE_DIR / corridor_id


def _corridor_metadata_path(corridor_id: str) -> Path:
    return _corridor_dir(corridor_id) / "metadata.json"


def _corridor_routes_path(corridor_id: str) -> Path:
    return _corridor_dir(corridor_id) / "corridor_routes_scored.json"


def _corridor_towers_path(corridor_id: str) -> Path:
    return _corridor_dir(corridor_id) / "opencellid_towers.json"


def purge_corridor_cache(corridor_id: str) -> bool:
    corridor_dir = _corridor_dir(corridor_id)
    if not corridor_dir.exists():
        return False

    for path in (
        _corridor_metadata_path(corridor_id),
        _corridor_routes_path(corridor_id),
        _corridor_towers_path(corridor_id),
    ):
        if path.exists():
            path.unlink()

    if corridor_dir.exists() and not any(corridor_dir.iterdir()):
        corridor_dir.rmdir()

    return True


def _normalize_city(name: str) -> str:
    return " ".join(name.strip().lower().split())


def build_corridor_id(source_city: str, destination_city: str) -> str:
    norm = f"{_normalize_city(source_city)}|{_normalize_city(destination_city)}|nominatim|osrm|opencellid"
    return hashlib.sha1(norm.encode("utf-8")).hexdigest()[:16]


def _request_json(
    base_url: str, params: dict[str, Any], timeout: int = 45
) -> dict[str, Any]:
    query = urlencode(params)
    req = Request(
        f"{base_url}?{query}",
        headers={
            "User-Agent": "node-zero-corridor-jobs/0.1",
            "Accept": "application/json",
        },
    )
    with urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def geocode_city(city: str) -> tuple[float, float, str]:
    payload = _request_json(
        "https://nominatim.openstreetmap.org/search",
        {
            "q": city,
            "format": "jsonv2",
            "limit": 1,
        },
        timeout=30,
    )
    if not payload:
        raise RuntimeError(f"Could not geocode city: {city}")

    first = payload[0]
    lat = float(first["lat"])
    lon = float(first["lon"])
    label = str(first.get("display_name", city))
    return lon, lat, label


def fetch_osrm_routes(
    origin: tuple[float, float], destination: tuple[float, float]
) -> list[dict[str, Any]]:
    payload = _request_json(
        f"https://router.project-osrm.org/route/v1/driving/{origin[0]},{origin[1]};{destination[0]},{destination[1]}",
        {
            "alternatives": "true",
            "overview": "full",
            "geometries": "geojson",
            "steps": "false",
        },
        timeout=45,
    )
    routes = payload.get("routes", [])
    if not routes:
        raise RuntimeError("OSRM did not return any routes")
    return routes[:3]


def _is_us_location(label: str) -> bool:
    lowered = label.lower()
    return "united states" in lowered or ", usa" in lowered or ", us" in lowered


def _dbm_to_tower_shape(dbm: float) -> tuple[float, int]:
    if dbm >= -90:
        return 2600.0, 42
    if dbm >= -100:
        return 1800.0, 28
    if dbm >= -110:
        return 1200.0, 16
    return 750.0, 8


def _lonlat_to_tile_xy(lon: float, lat: float, zoom: int) -> tuple[int, int]:
    lat_rad = math.radians(lat)
    n = 2**zoom
    x = int((lon + 180.0) / 360.0 * n)
    y = int(
        (1.0 - math.log(math.tan(lat_rad) + 1 / math.cos(lat_rad)) / math.pi) / 2.0 * n
    )
    x = max(0, min(n - 1, x))
    y = max(0, min(n - 1, y))
    return x, y


def _tiles_for_routes(
    routes: list[dict[str, Any]], zoom: int = 9
) -> set[tuple[int, int, int]]:
    tiles: set[tuple[int, int, int]] = set()
    for route in routes:
        for lon, lat in route["geometry"]["coordinates"]:
            x, y = _lonlat_to_tile_xy(lon, lat, zoom)
            tiles.add((zoom, x, y))

            for dx in (0,):
                for dy in (0,):
                    nx = x + dx
                    ny = y + dy
                    if nx >= 0 and ny >= 0:
                        tiles.add((zoom, nx, ny))

    if len(tiles) > 12:
        ordered = sorted(tiles)
        stride = max(1, math.ceil(len(ordered) / 12))
        tiles = set(ordered[::stride][:12])

    return tiles


def _extract_dbm_from_properties(props: dict[str, Any]) -> float | None:
    for key in (
        "signal",
        "signalDbm",
        "dbm",
        "rsrp",
        "avgSignal",
        "averageSignal",
        "signal_strength",
        "value",
    ):
        value = props.get(key)
        if isinstance(value, (int, float)):
            return float(value)

    for value in props.values():
        if isinstance(value, (int, float)) and -150 <= float(value) <= -40:
            return float(value)

    return None


def _center_from_geometry(geometry: dict[str, Any]) -> tuple[float, float] | None:
    gtype = geometry.get("type")
    coords = geometry.get("coordinates")
    if gtype == "Point" and isinstance(coords, (list, tuple)) and len(coords) >= 2:
        return float(coords[0]), float(coords[1])
    if gtype == "MultiPoint" and isinstance(coords, list) and coords:
        first = coords[0]
        if isinstance(first, (list, tuple)) and len(first) >= 2:
            return float(first[0]), float(first[1])
    if gtype == "LineString" and isinstance(coords, list) and coords:
        xs = [pt[0] for pt in coords if isinstance(pt, (list, tuple)) and len(pt) >= 2]
        ys = [pt[1] for pt in coords if isinstance(pt, (list, tuple)) and len(pt) >= 2]
        if xs and ys:
            return float(sum(xs) / len(xs)), float(sum(ys) / len(ys))
    if gtype == "Polygon" and isinstance(coords, list):
        ring_points: list[tuple[float, float]] = []
        for ring in coords:
            if not isinstance(ring, list):
                continue
            for point in ring:
                if isinstance(point, (list, tuple)) and len(point) >= 2:
                    ring_points.append((float(point[0]), float(point[1])))
        if ring_points:
            xs = [point[0] for point in ring_points]
            ys = [point[1] for point in ring_points]
            return float(sum(xs) / len(xs)), float(sum(ys) / len(ys))
    return None


def _fetch_coveragemap_tile(
    api_key: str, provider_code: str, z: int, x: int, y: int
) -> bytes:
    query = urlencode({"technology": "4G", "apiKey": api_key})
    req = Request(
        f"https://enterprise.coveragemap.com/api/v1/signal-strength/tiles/{provider_code}/{z}/{x}/{y}?{query}",
        headers={
            "Accept": "application/x-protobuf,application/octet-stream,*/*",
            "Authorization": f"Bearer {api_key}",
            "User-Agent": "node-zero-corridor-jobs/0.1",
        },
    )
    try:
        with urlopen(req, timeout=30) as response:
            return response.read()
    except HTTPError as exc:
        if exc.code == 429:
            time.sleep(1.2)
            with urlopen(req, timeout=30) as response:
                return response.read()
        raise


def fetch_coveragemap_towers(
    api_key: str, routes: list[dict[str, Any]]
) -> tuple[list[Tower], dict[str, str], str, int, str | None]:
    tiles = _tiles_for_routes(routes, zoom=9)
    provider_candidates = [
        ("ATT", "AT&T"),
        ("TMO", "T-Mobile"),
        ("VZW", "Verizon"),
    ]

    provider_samples: dict[str, list[tuple[float, float, float]]] = {
        code: [] for code, _ in provider_candidates
    }
    request_count = 0
    errors: dict[str, int] = {}
    saw_429 = False

    for z, x, y in tiles:
        for code, _ in provider_candidates:
            try:
                raw = _fetch_coveragemap_tile(api_key, code, z, x, y)
                decoded = mapbox_vector_tile.decode(raw)
                error_code = None
            except HTTPError as exc:
                body = ""
                try:
                    body = exc.read().decode("utf-8")
                except Exception:
                    body = ""
                if exc.code == 429:
                    saw_429 = True
                if "API key is not valid for this product" in body:
                    error_code = "coveragemap_key_not_valid_for_tiles"
                else:
                    error_code = f"coveragemap_http_{exc.code}"
                decoded = {}
            except Exception:
                error_code = "coveragemap_tile_decode_failed"
                decoded = {}

            request_count += 1
            if error_code:
                errors[error_code] = errors.get(error_code, 0) + 1
                continue

            for layer in decoded.values():
                features = layer.get("features", []) if isinstance(layer, dict) else []
                for feature in features:
                    props = feature.get("properties", {})
                    dbm = _extract_dbm_from_properties(
                        props if isinstance(props, dict) else {}
                    )
                    if dbm is None:
                        continue
                    center = _center_from_geometry(feature.get("geometry", {}))
                    if not center:
                        continue
                    provider_samples[code].append((center[1], center[0], dbm))

        time.sleep(0.06 if not saw_429 else 0.25)

    ranked = sorted(
        provider_candidates,
        key=lambda item: (
            len(provider_samples[item[0]]),
            sum(v[2] for v in provider_samples[item[0]])
            / max(1, len(provider_samples[item[0]])),
        ),
        reverse=True,
    )

    primary = ranked[0]
    secondary = ranked[1] if len(ranked) > 1 else ranked[0]
    slot_map = {"jio": primary, "airtel": secondary}

    OPERATOR_MNC_MAP["jio"] = {(999, 1)}
    OPERATOR_MNC_MAP["airtel"] = {(999, 2)}

    towers: list[Tower] = []
    for slot, (provider_code, _) in slot_map.items():
        mnc = 1 if slot == "jio" else 2
        for lat, lon, dbm in provider_samples[provider_code]:
            range_m, samples = _dbm_to_tower_shape(dbm)
            towers.append(
                Tower(
                    lat=lat,
                    lon=lon,
                    mcc=999,
                    mnc=mnc,
                    lac=0,
                    cellid=int(abs(hash((provider_code, lat, lon))) % 1_000_000_000),
                    radio="LTE",
                    range_m=range_m,
                    samples=samples,
                )
            )

    labels = {
        "jio": f"{primary[1]} (CoverageMap)",
        "airtel": f"{secondary[1]} (CoverageMap)",
    }
    note = "Operator buckets are mapped from top CoverageMap providers for this U.S. corridor."
    error_hint = None
    if not towers and errors:
        error_hint = max(errors.items(), key=lambda item: item[1])[0]
    elif saw_429:
        error_hint = "coveragemap_rate_limited"

    return towers, labels, note, request_count, error_hint


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
    if len(geometry) < 2:
        return segments

    carry_start = (geometry[0][0], geometry[0][1])
    carry_remaining = segment_length_m

    for index in range(1, len(geometry)):
        start = carry_start
        end = (geometry[index][0], geometry[index][1])
        distance = haversine_meters(start[0], start[1], end[0], end[1])
        if distance == 0:
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

            if carry_remaining <= 1e-6 or (progress + step) >= distance:
                segments.append(
                    {
                        "start_lon": seg_start[0],
                        "start_lat": seg_start[1],
                        "end_lon": seg_end[0],
                        "end_lat": seg_end[1],
                    }
                )
                carry_start = seg_end
                carry_remaining = segment_length_m

            progress += step

    return segments


def sample_tile_centers(
    routes: list[dict[str, Any]],
    interval_m: float = 9000,
    max_tile_centers: int = 18,
) -> list[tuple[float, float]]:
    centers: list[tuple[float, float]] = []
    seen: set[str] = set()

    for route in routes:
        geometry = route["geometry"]["coordinates"]
        acc = 0.0
        next_mark = 0.0

        for idx in range(1, len(geometry)):
            p1 = geometry[idx - 1]
            p2 = geometry[idx]
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

    if len(centers) > max_tile_centers:
        step = max(1, math.ceil(len(centers) / max_tile_centers))
        centers = centers[::step][:max_tile_centers]

    return centers


def _fetch_bbox_cells(
    api_key: str,
    lat: float,
    lon: float,
    delta: float,
    stats: FetchStats,
) -> list[dict[str, Any]]:
    payload = _request_json(
        "https://opencellid.org/cell/getInArea",
        {
            "key": api_key,
            "BBOX": f"{lat - delta:.6f},{lon - delta:.6f},{lat + delta:.6f},{lon + delta:.6f}",
            "format": "json",
        },
        timeout=45,
    )
    stats.requests += 1
    if payload.get("error") and payload.get("code") != 1:
        stats.payload_errors += 1
        return []
    return payload.get("cells", [])


def _fetch_bbox_recursive(
    api_key: str,
    lat: float,
    lon: float,
    delta: float,
    depth: int = 0,
    max_depth: int = 1,
    stats: FetchStats | None = None,
) -> list[dict[str, Any]]:
    if stats is None:
        stats = FetchStats()

    try:
        cells = _fetch_bbox_cells(api_key, lat, lon, delta, stats)
    except Exception:
        stats.http_errors += 1
        return []

    if len(cells) < 50 or depth >= max_depth or delta <= 0.002:
        return cells

    stats.split_tiles += 1
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
    delta = 0.009
    stats = FetchStats()
    towers: dict[tuple[Any, ...], Tower] = {}

    for lat, lon in centers:
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

        time.sleep(0.05)

    return list(towers.values())


def operator_for_tower(tower: Tower) -> str | None:
    key = (tower.mcc, tower.mnc)
    for operator, mapped in OPERATOR_MNC_MAP.items():
        if key in mapped:
            return operator
    return None


def _derive_operator_profile(towers: list[Tower]) -> tuple[dict[str, str], str | None]:
    if not towers:
        return {"jio": "Operator A", "airtel": "Operator B"}, (
            "No tower data available yet; using generic operator labels."
        )

    counts: dict[tuple[int, int], int] = {}
    for tower in towers:
        key = (tower.mcc, tower.mnc)
        counts[key] = counts.get(key, 0) + 1

    ranked = sorted(counts.items(), key=lambda item: item[1], reverse=True)
    top_one = ranked[0][0] if ranked else None
    top_two = ranked[1][0] if len(ranked) > 1 else None

    if top_one:
        OPERATOR_MNC_MAP["jio"] = {top_one}
    if top_two:
        OPERATOR_MNC_MAP["airtel"] = {top_two}
    elif top_one:
        OPERATOR_MNC_MAP["airtel"] = {top_one}

    mcc = top_one[0] if top_one else 0
    label_a = f"MCC {top_one[0]} MNC {top_one[1]}" if top_one else "Operator A"
    label_b = f"MCC {top_two[0]} MNC {top_two[1]}" if top_two else "Operator B"
    note = (
        f"Auto-mapped operator buckets for MCC {mcc} using dominant MNCs in this corridor."
        if mcc
        else "Auto-mapped operator buckets using dominant MNCs in this corridor."
    )

    return {"jio": label_a, "airtel": label_b}, note


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
    if operator == "all":
        all_candidates: list[tuple[float, float]] = []
        for tower in towers:
            distance = haversine_meters(
                midpoint_lon, midpoint_lat, tower.lon, tower.lat
            )
            if distance > 3500:
                continue

            radio_weight = RADIO_WEIGHTS.get(tower.radio.upper(), 0.22)
            quality = _tower_quality_weight(tower)
            distance_decay = math.exp(-distance / max(350.0, tower.range_m * 0.9))
            contribution = radio_weight * quality * distance_decay
            all_candidates.append((distance, contribution))

        all_candidates.sort(key=lambda item: item[0])
        return sum(score for _, score in all_candidates[:12])

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


def _percentile(values: list[float], q: float) -> float:
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


def normalize_scores(raw_scores: list[float], floor: float = 18.0) -> list[float]:
    if not raw_scores:
        return []

    non_zero = [value for value in raw_scores if value > 0]
    if not non_zero:
        return [floor * 0.6 for _ in raw_scores]

    p10 = _percentile(non_zero, 0.10)
    p90 = _percentile(non_zero, 0.90)

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
    all_networks_raw: list[float] = []
    all_jio_raw: list[float] = []
    all_airtel_raw: list[float] = []

    for route in routes:
        geometry = route["geometry"]["coordinates"]
        segments = segmentize_geometry(geometry)

        jio_raw: list[float] = []
        airtel_raw: list[float] = []
        all_raw: list[float] = []

        for segment in segments:
            midpoint_lon = (segment["start_lon"] + segment["end_lon"]) / 2
            midpoint_lat = (segment["start_lat"] + segment["end_lat"]) / 2
            jio_raw.append(
                score_segment_for_operator(midpoint_lon, midpoint_lat, towers, "jio")
            )
            airtel_raw.append(
                score_segment_for_operator(midpoint_lon, midpoint_lat, towers, "airtel")
            )
            all_raw.append(
                score_segment_for_operator(midpoint_lon, midpoint_lat, towers, "all")
            )

        all_networks_raw.extend(all_raw)
        all_jio_raw.extend(jio_raw)
        all_airtel_raw.extend(airtel_raw)
        route_intermediate.append(
            {
                "route": route,
                "segments": segments,
                "all_raw": all_raw,
                "jio_raw": jio_raw,
                "airtel_raw": airtel_raw,
            }
        )

    all_networks_norm = normalize_scores(all_networks_raw, floor=18.0)
    jio_all_norm = normalize_scores(all_jio_raw, floor=18.0)
    airtel_all_norm = normalize_scores(all_airtel_raw, floor=18.0)

    all_cursor = 0
    jio_cursor = 0
    airtel_cursor = 0
    for idx, item in enumerate(route_intermediate):
        route = item["route"]
        segments = item["segments"]
        all_len = len(item["all_raw"])
        jio_len = len(item["jio_raw"])
        airtel_len = len(item["airtel_raw"])

        all_norm = all_networks_norm[all_cursor : all_cursor + all_len]
        jio_norm = jio_all_norm[jio_cursor : jio_cursor + jio_len]
        airtel_norm = airtel_all_norm[airtel_cursor : airtel_cursor + airtel_len]
        all_cursor += all_len
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
                        "all": all_norm[seg_idx] if seg_idx < len(all_norm) else 0.0,
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


def _persist_job(job: dict[str, Any]) -> None:
    _job_path(job["job_id"]).write_text(json.dumps(job, indent=2), encoding="utf-8")


def _update_job(job_id: str, **updates: Any) -> None:
    with _lock:
        job = _jobs[job_id]
        job.update(updates)
        _persist_job(job)


def _corridor_cache_fresh(corridor_id: str) -> bool:
    meta_path = _corridor_metadata_path(corridor_id)
    if not meta_path.exists():
        return False
    try:
        payload = json.loads(meta_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False

    expires_at = int(payload.get("expires_at", 0))
    routes_ok = _corridor_routes_path(corridor_id).exists()
    towers_ok = _corridor_towers_path(corridor_id).exists()
    return expires_at > _now() and routes_ok and towers_ok


def _write_corridor_cache(
    corridor_id: str,
    source_city: str,
    destination_city: str,
    source_label: str,
    destination_label: str,
    scored_routes: list[dict[str, Any]],
    towers: list[Tower],
    operator_labels: dict[str, str],
    operator_note: str | None,
    degraded: bool,
    degraded_reason: str | None,
) -> None:
    corridor_dir = _corridor_dir(corridor_id)
    corridor_dir.mkdir(parents=True, exist_ok=True)

    now = _now()
    routes_path = _corridor_routes_path(corridor_id)
    towers_path = _corridor_towers_path(corridor_id)

    routes_path.write_text(
        json.dumps(
            {
                "source": "osrm+opencellid-dynamic",
                "corridor": f"{source_city}-{destination_city}",
                "corridor_id": corridor_id,
                "generated_at": now,
                "route_count": len(scored_routes),
                "tower_count": len(towers),
                "operator_labels": operator_labels,
                "operator_note": operator_note,
                "degraded": degraded,
                "degraded_reason": degraded_reason,
                "routes": scored_routes,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    towers_path.write_text(
        json.dumps(
            {
                "source": "opencellid-dynamic",
                "corridor": f"{source_city}-{destination_city}",
                "corridor_id": corridor_id,
                "generated_at": now,
                "tower_count": len(towers),
                "operator_labels": operator_labels,
                "operator_note": operator_note,
                "degraded": degraded,
                "degraded_reason": degraded_reason,
                "towers": serialize_towers(towers),
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    _corridor_metadata_path(corridor_id).write_text(
        json.dumps(
            {
                "corridor_id": corridor_id,
                "source_city": source_city,
                "destination_city": destination_city,
                "source_label": source_label,
                "destination_label": destination_label,
                "generated_at": now,
                "expires_at": now + TTL_SECONDS,
                "degraded": degraded,
                "degraded_reason": degraded_reason,
                "route_count": len(scored_routes),
                "tower_count": len(towers),
                "operator_labels": operator_labels,
                "operator_note": operator_note,
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def _run_job(job_id: str) -> None:
    with _lock:
        job = _jobs[job_id]
        source_city = job["source_city"]
        destination_city = job["destination_city"]
        corridor_id = job["corridor_id"]

    try:
        _update_job(
            job_id, status="geocoding", stage="Geocoding cities", progress_pct=15
        )
        origin_lon, origin_lat, source_label = geocode_city(source_city)
        dest_lon, dest_lat, destination_label = geocode_city(destination_city)

        _update_job(
            job_id, status="routing", stage="Fetching OSRM routes", progress_pct=35
        )
        routes = fetch_osrm_routes((origin_lon, origin_lat), (dest_lon, dest_lat))

        _update_job(
            job_id,
            status="tower_fetch",
            stage="Fetching OpenCellID towers",
            progress_pct=60,
        )
        opencellid_api_key = os.getenv("OPENCELLID_API_KEY", "").strip()
        coveragemap_api_key = os.getenv("COVERAGE_MAP", "").strip()
        provider_mode = os.getenv("COVERAGE_PROVIDER", "auto").strip().lower()
        degraded = False
        degraded_reason: str | None = None
        request_count = 0
        coverage_error_hint: str | None = None

        towers: list[Tower]
        operator_labels: dict[str, str]
        operator_note: str | None
        use_coveragemap = provider_mode == "coveragemap" or (
            provider_mode == "auto"
            and coveragemap_api_key
            and _is_us_location(source_label)
            and _is_us_location(destination_label)
        )

        if use_coveragemap:
            _update_job(
                job_id,
                status="tower_fetch",
                stage="Fetching CoverageMap lookups",
                progress_pct=60,
            )
            if not coveragemap_api_key:
                towers = []
                degraded = True
                degraded_reason = "COVERAGE_MAP is not configured"
                operator_labels, operator_note = _derive_operator_profile(towers)
            else:
                (
                    towers,
                    operator_labels,
                    operator_note,
                    request_count,
                    coverage_error_hint,
                ) = fetch_coveragemap_towers(coveragemap_api_key, routes)
                if coverage_error_hint in {
                    "coveragemap_key_not_valid_for_lookup",
                    "coveragemap_key_not_valid_for_tiles",
                    "coveragemap_rate_limited",
                    "coveragemap_http_429",
                }:
                    if opencellid_api_key:
                        _update_job(
                            job_id,
                            status="tower_fetch",
                            stage="CoverageMap unavailable for this request; falling back to OpenCellID",
                            progress_pct=60,
                        )
                        towers = fetch_opencellid_towers(opencellid_api_key, routes)
                        operator_labels, operator_note = _derive_operator_profile(
                            towers
                        )
                        degraded = len(towers) < 50
                        degraded_reason = (
                            f"Fallback OpenCellID returned too few towers ({len(towers)}). Connectivity confidence is low."
                            if degraded
                            else None
                        )
                        use_coveragemap = False
                    else:
                        degraded = True
                        degraded_reason = "CoverageMap key cannot access required endpoint and OPENCELLID_API_KEY is not configured for fallback."
                if use_coveragemap and len(towers) < 20:
                    degraded = True
                    degraded_reason = (
                        f"CoverageMap returned too few samples ({len(towers)})."
                    )
        else:
            _update_job(
                job_id,
                status="tower_fetch",
                stage="Fetching OpenCellID towers",
                progress_pct=60,
            )
            if not opencellid_api_key:
                towers = []
                degraded = True
                degraded_reason = "OPENCELLID_API_KEY is not configured"
            else:
                towers = fetch_opencellid_towers(opencellid_api_key, routes)
                if len(towers) < 50:
                    degraded = True
                    degraded_reason = f"Too few towers returned ({len(towers)}). Connectivity confidence is low."

            operator_labels, operator_note = _derive_operator_profile(towers)

        if use_coveragemap:
            operator_note = (
                f"{operator_note} Approx API lookups used: {request_count}."
                if operator_note
                else f"Approx API lookups used: {request_count}."
            )

        _update_job(job_id, status="scoring", stage="Scoring routes", progress_pct=85)
        scored_routes = build_scored_routes(routes, towers)

        _write_corridor_cache(
            corridor_id=corridor_id,
            source_city=source_city,
            destination_city=destination_city,
            source_label=source_label,
            destination_label=destination_label,
            scored_routes=scored_routes,
            towers=towers,
            operator_labels=operator_labels,
            operator_note=operator_note,
            degraded=degraded,
            degraded_reason=degraded_reason,
        )

        status: Literal["ready", "ready_degraded"] = (
            "ready_degraded" if degraded else "ready"
        )
        _update_job(
            job_id,
            status=status,
            stage="Completed",
            progress_pct=100,
            degraded=degraded,
            degraded_reason=degraded_reason,
            source_label=source_label,
            destination_label=destination_label,
            tower_count=len(towers),
            route_count=len(scored_routes),
            completed_at=_now(),
        )
    except Exception as exc:
        _update_job(
            job_id,
            status="failed",
            stage="Failed",
            progress_pct=100,
            error=str(exc),
            completed_at=_now(),
        )


def create_corridor_job(
    source_city: str, destination_city: str, force_refresh: bool = False
) -> dict[str, Any]:
    if not source_city.strip() or not destination_city.strip():
        raise RuntimeError("source_city and destination_city are required")

    corridor_id = build_corridor_id(source_city, destination_city)
    job_id = hashlib.sha1(f"{corridor_id}:{_now()}".encode("utf-8")).hexdigest()[:16]

    if force_refresh:
        purge_corridor_cache(corridor_id)

    if _corridor_cache_fresh(corridor_id):
        job = {
            "job_id": job_id,
            "corridor_id": corridor_id,
            "source_city": source_city,
            "destination_city": destination_city,
            "status": "ready",
            "stage": "Cache hit",
            "progress_pct": 100,
            "degraded": False,
            "degraded_reason": None,
            "error": None,
            "created_at": _now(),
            "completed_at": _now(),
        }
        with _lock:
            _jobs[job_id] = job
            _persist_job(job)
        return job

    job = {
        "job_id": job_id,
        "corridor_id": corridor_id,
        "source_city": source_city,
        "destination_city": destination_city,
        "status": "queued",
        "stage": "Queued",
        "progress_pct": 0,
        "degraded": False,
        "degraded_reason": None,
        "error": None,
        "tower_count": 0,
        "route_count": 0,
        "created_at": _now(),
        "completed_at": None,
    }
    with _lock:
        _jobs[job_id] = job
        _persist_job(job)

    _executor.submit(_run_job, job_id)
    return job


def get_corridor_job(job_id: str) -> dict[str, Any] | None:
    with _lock:
        if job_id in _jobs:
            return dict(_jobs[job_id])

    path = _job_path(job_id)
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None

    with _lock:
        _jobs[job_id] = payload
    return payload
