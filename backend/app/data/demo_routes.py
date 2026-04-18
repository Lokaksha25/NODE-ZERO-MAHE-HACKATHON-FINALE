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


_CACHE_PATH = Path(__file__).resolve().parents[3] / "data" / "cache" / "corridor_routes_scored.json"


def _read_cache_payload() -> dict | None:
    if not _CACHE_PATH.exists():
        return None

    try:
        return json.loads(_CACHE_PATH.read_text(encoding="utf-8"))
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
    value = raw_scores.get(operator.value, 0.0)
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _load_cached_routes() -> list[RouteTemplate]:
    payload = _read_cache_payload()
    if not payload:
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
                        Operator.jio: _parse_operator_score(raw_scores, Operator.jio),
                        Operator.airtel: _parse_operator_score(raw_scores, Operator.airtel),
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


def get_demo_routes() -> list[RouteTemplate]:
    cached = _load_cached_routes()
    if cached:
        return cached
    return _fallback_routes()


def get_data_source_status() -> dict[str, int | str | bool]:
    payload = _read_cache_payload()
    if not payload:
        fallback = _fallback_routes()
        return {
            "source_mode": "fallback",
            "source_name": "synthetic-demo",
            "cache_exists": False,
            "route_count": len(fallback),
            "tower_count": 0,
            "generated_at": 0,
        }

    routes = payload.get("routes", [])
    return {
        "source_mode": "cached",
        "source_name": str(payload.get("source", "osrm+opencellid")),
        "cache_exists": True,
        "route_count": int(payload.get("route_count", len(routes))),
        "tower_count": int(payload.get("tower_count", 0)),
        "generated_at": int(payload.get("generated_at", 0)),
    }
