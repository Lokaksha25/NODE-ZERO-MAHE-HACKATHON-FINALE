from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from app.core.models import Operator


@dataclass(frozen=True)
class SegmentTemplate:
    start_lon: float
    start_lat: float
    end_lon: float
    end_lat: float
    scores: dict[Operator, float]


@dataclass(frozen=True)
class RouteTemplate:
    route_id: str
    label: str
    distance_km: float
    eta_minutes: int
    geometry: list[tuple[float, float]]
    segments: list[SegmentTemplate]


def _resolve_cache_path() -> Path:
    here = Path(__file__).resolve()
    candidates = [
        here.parents[2] / "data" / "cache" / "corridor_routes_scored.json",
        here.parents[3] / "data" / "cache" / "corridor_routes_scored.json",
        Path("/app/data/cache/corridor_routes_scored.json"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


_CACHE_PATH = _resolve_cache_path()


def _resolve_towers_cache_path(corridor_id: str | None = None) -> Path:
    here = Path(__file__).resolve()

    if corridor_id:
        candidates = [
            here.parents[2]
            / "data"
            / "cache"
            / "corridors"
            / corridor_id
            / "opencellid_towers.json",
            here.parents[3]
            / "data"
            / "cache"
            / "corridors"
            / corridor_id
            / "opencellid_towers.json",
            Path("/app/data/cache/corridors") / corridor_id / "opencellid_towers.json",
        ]
    else:
        candidates = [
            here.parents[2] / "data" / "cache" / "opencellid_towers.json",
            here.parents[3] / "data" / "cache" / "opencellid_towers.json",
            Path("/app/data/cache/opencellid_towers.json"),
        ]

    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def _infer_operator_profile(
    corridor_id: str | None,
) -> tuple[dict[str, str] | None, str | None]:
    towers_path = _resolve_towers_cache_path(corridor_id=corridor_id)
    if not towers_path.exists():
        return None, None

    try:
        payload = json.loads(towers_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None, None

    counts: dict[tuple[int, int], int] = {}
    for tower in payload.get("towers", []):
        try:
            key = (int(tower.get("mcc", 0)), int(tower.get("mnc", 0)))
        except (TypeError, ValueError):
            continue
        counts[key] = counts.get(key, 0) + 1

    ranked = sorted(counts.items(), key=lambda item: item[1], reverse=True)
    if not ranked:
        return None, None

    first = ranked[0][0]
    second = ranked[1][0] if len(ranked) > 1 else ranked[0][0]

    labels = {
        "jio": f"MCC {first[0]} MNC {first[1]}",
        "airtel": f"MCC {second[0]} MNC {second[1]}",
    }
    note = f"Auto-mapped operator buckets for MCC {first[0]} using dominant MNCs in this corridor."
    return labels, note


def _resolve_dynamic_cache_path(corridor_id: str) -> Path:
    here = Path(__file__).resolve()
    candidates = [
        here.parents[2]
        / "data"
        / "cache"
        / "corridors"
        / corridor_id
        / "corridor_routes_scored.json",
        here.parents[3]
        / "data"
        / "cache"
        / "corridors"
        / corridor_id
        / "corridor_routes_scored.json",
        Path("/app/data/cache/corridors") / corridor_id / "corridor_routes_scored.json",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def _read_cache_payload(corridor_id: str | None = None) -> dict | None:
    path = _resolve_dynamic_cache_path(corridor_id) if corridor_id else _CACHE_PATH
    if not path.exists():
        return None

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def _resolve_corridor_summary_path(corridor: str | None) -> Path | None:
    if not corridor:
        return None

    here = Path(__file__).resolve()
    candidates = [
        here.parents[2]
        / "data"
        / "cache"
        / "corridor_csv"
        / f"{corridor}-242-summary.json",
        here.parents[3]
        / "data"
        / "cache"
        / "corridor_csv"
        / f"{corridor}-242-summary.json",
        Path("/app/data/cache/corridor_csv") / f"{corridor}-242-summary.json",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def _read_corridor_summary(corridor: str | None) -> dict | None:
    summary_path = _resolve_corridor_summary_path(corridor)
    if not summary_path:
        return None

    try:
        return json.loads(summary_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def _interpolate_points(
    start: tuple[float, float],
    end: tuple[float, float],
    steps: int,
    wobble: float = 0.0,
) -> list[tuple[float, float]]:
    points: list[tuple[float, float]] = []
    for idx in range(steps + 1):
        t = idx / steps
        lon = start[0] + (end[0] - start[0]) * t
        lat = start[1] + (end[1] - start[1]) * t
        if wobble:
            lon += wobble * (0.5 - abs(0.5 - t))
        points.append((lon, lat))
    return points


def _build_segments(
    points: list[tuple[float, float]],
    jio_scores: list[float],
    airtel_scores: list[float],
) -> list[SegmentTemplate]:
    segments: list[SegmentTemplate] = []
    for idx in range(len(points) - 1):
        segments.append(
            SegmentTemplate(
                start_lon=points[idx][0],
                start_lat=points[idx][1],
                end_lon=points[idx + 1][0],
                end_lat=points[idx + 1][1],
                scores={
                    Operator.all: round((jio_scores[idx] + airtel_scores[idx]) / 2, 2),
                    Operator.jio: jio_scores[idx],
                    Operator.airtel: airtel_scores[idx],
                },
            )
        )
    return segments


def _fallback_routes() -> list[RouteTemplate]:
    origin = (77.6173, 12.9352)
    destination = (76.6558, 12.3052)

    fast_points = _interpolate_points(origin, destination, 15, wobble=-0.02)
    connected_points = _interpolate_points(origin, destination, 16, wobble=0.028)
    balanced_points = _interpolate_points(origin, destination, 15, wobble=0.01)

    return [
        RouteTemplate(
            route_id="fast_corridor",
            label="Route A - Fastest (fallback)",
            distance_km=141.4,
            eta_minutes=165,
            geometry=fast_points,
            segments=_build_segments(
                fast_points,
                [72, 68, 61, 55, 49, 40, 36, 34, 38, 44, 52, 59, 63, 67, 70],
                [75, 72, 68, 62, 58, 51, 47, 45, 50, 56, 62, 66, 69, 72, 74],
            ),
        ),
        RouteTemplate(
            route_id="connected_corridor",
            label="Route B - Most Connected (fallback)",
            distance_km=148.7,
            eta_minutes=181,
            geometry=connected_points,
            segments=_build_segments(
                connected_points,
                [70, 72, 74, 76, 71, 68, 66, 64, 67, 70, 72, 74, 76, 73, 71, 69],
                [62, 64, 66, 63, 59, 54, 49, 46, 52, 58, 63, 65, 67, 66, 64, 62],
            ),
        ),
        RouteTemplate(
            route_id="balanced_corridor",
            label="Route C - Balanced (fallback)",
            distance_km=145.2,
            eta_minutes=173,
            geometry=balanced_points,
            segments=_build_segments(
                balanced_points,
                [68, 66, 64, 62, 58, 54, 50, 47, 49, 53, 58, 62, 65, 67, 68],
                [69, 68, 66, 64, 61, 57, 53, 50, 52, 56, 60, 63, 66, 68, 69],
            ),
        ),
    ]


def _parse_operator_score(raw_scores: dict[str, float], operator: Operator) -> float:
    value = raw_scores.get(operator.value)
    if value is None and operator == Operator.all:
        value = raw_scores.get("jio", 0.0)
    if value is None:
        value = 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _load_cached_routes(corridor_id: str | None = None) -> list[RouteTemplate]:
    payload = _read_cache_payload(corridor_id=corridor_id)
    if not payload:
        return []

    if int(payload.get("tower_count", 0)) < 50:
        return []

    routes = payload.get("routes", [])
    parsed: list[RouteTemplate] = []

    for route in routes:
        segments: list[SegmentTemplate] = []
        for segment in route.get("segments", []):
            raw_scores = segment.get("scores", {})
            segments.append(
                SegmentTemplate(
                    start_lon=float(segment["start_lon"]),
                    start_lat=float(segment["start_lat"]),
                    end_lon=float(segment["end_lon"]),
                    end_lat=float(segment["end_lat"]),
                    scores={
                        Operator.all: _parse_operator_score(raw_scores, Operator.all),
                        Operator.jio: _parse_operator_score(raw_scores, Operator.jio),
                        Operator.airtel: _parse_operator_score(
                            raw_scores, Operator.airtel
                        ),
                    },
                )
            )

        geometry = [
            (float(point[0]), float(point[1]))
            for point in route.get("geometry", [])
            if isinstance(point, list) and len(point) == 2
        ]

        if not geometry or not segments:
            continue

        parsed.append(
            RouteTemplate(
                route_id=str(route.get("route_id", "unknown_route")),
                label=str(route.get("label", "Route")),
                distance_km=float(route.get("distance_km", 0.0)),
                eta_minutes=int(route.get("eta_minutes", 0)),
                geometry=geometry,
                segments=segments,
            )
        )

    return parsed


def get_demo_routes(corridor_id: str | None = None) -> list[RouteTemplate]:
    cached = _load_cached_routes(corridor_id=corridor_id)
    if cached:
        return cached
    return []


def get_data_source_status(
    corridor_id: str | None = None,
) -> dict[str, int | str | bool | None]:
    payload = _read_cache_payload(corridor_id=corridor_id)
    if not payload:
        return {
            "source_mode": "no_data",
            "source_name": "none",
            "corridor": None,
            "cache_exists": False,
            "route_count": 0,
            "tower_count": 0,
            "generated_at": 0,
        }

    corridor = str(payload.get("corridor", "unknown-corridor"))
    corridor_summary = _read_corridor_summary(corridor)
    corridor_tower_count = (
        int(corridor_summary.get("row_count", 0)) if corridor_summary else 0
    )
    degraded = bool(payload.get("degraded", False))
    degraded_reason = payload.get("degraded_reason")
    operator_labels = payload.get("operator_labels")
    operator_note = payload.get("operator_note")
    if operator_labels is None:
        inferred_labels, inferred_note = _infer_operator_profile(
            corridor_id=corridor_id
        )
        operator_labels = inferred_labels
        operator_note = inferred_note

    if int(payload.get("tower_count", 0)) < 50:
        fallback = _fallback_routes()
        return {
            "source_mode": "fallback",
            "source_name": "synthetic-demo",
            "corridor": corridor,
            "corridor_id": corridor_id,
            "cache_exists": False,
            "route_count": len(fallback),
            "tower_count": corridor_tower_count or int(payload.get("tower_count", 0)),
            "generated_at": int(payload.get("generated_at", 0)),
            "degraded": degraded,
            "degraded_reason": degraded_reason,
            "operator_labels": operator_labels,
            "operator_note": operator_note,
        }

    routes = payload.get("routes", [])
    return {
        "source_mode": "cached",
        "source_name": str(payload.get("source", "osrm+opencellid")),
        "corridor": corridor,
        "corridor_id": corridor_id,
        "cache_exists": True,
        "route_count": int(payload.get("route_count", len(routes))),
        "tower_count": corridor_tower_count or int(payload.get("tower_count", 0)),
        "generated_at": int(payload.get("generated_at", 0)),
        "degraded": degraded,
        "degraded_reason": degraded_reason,
        "operator_labels": operator_labels,
        "operator_note": operator_note,
    }
