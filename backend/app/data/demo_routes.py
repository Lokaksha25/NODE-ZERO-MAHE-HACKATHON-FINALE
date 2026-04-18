from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

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


_origin = (77.6173, 12.9352)
_destination = (76.6558, 12.3052)

_fast_points = _interpolate_points(_origin, _destination, 15, wobble=-0.02)
_connected_points = _interpolate_points(_origin, _destination, 16, wobble=0.028)
_balanced_points = _interpolate_points(_origin, _destination, 15, wobble=0.01)

_demo_routes: list[RouteTemplate] = [
    RouteTemplate(
        route_id="fast_corridor",
        label="Route A - Fastest",
        distance_km=141.4,
        eta_minutes=165,
        geometry=_fast_points,
        segments=_build_segments(
            _fast_points,
            [72, 68, 61, 55, 49, 40, 36, 34, 38, 44, 52, 59, 63, 67, 70],
            [75, 72, 68, 62, 58, 51, 47, 45, 50, 56, 62, 66, 69, 72, 74],
        ),
    ),
    RouteTemplate(
        route_id="connected_corridor",
        label="Route B - Most Connected",
        distance_km=148.7,
        eta_minutes=181,
        geometry=_connected_points,
        segments=_build_segments(
            _connected_points,
            [70, 72, 74, 76, 71, 68, 66, 64, 67, 70, 72, 74, 76, 73, 71, 69],
            [62, 64, 66, 63, 59, 54, 49, 46, 52, 58, 63, 65, 67, 66, 64, 62],
        ),
    ),
    RouteTemplate(
        route_id="balanced_corridor",
        label="Route C - Balanced",
        distance_km=145.2,
        eta_minutes=173,
        geometry=_balanced_points,
        segments=_build_segments(
            _balanced_points,
            [68, 66, 64, 62, 58, 54, 50, 47, 49, 53, 58, 62, 65, 67, 68],
            [69, 68, 66, 64, 61, 57, 53, 50, 52, 56, 60, 63, 66, 68, 69],
        ),
    ),
]


def get_demo_routes() -> list[RouteTemplate]:
    return _demo_routes
