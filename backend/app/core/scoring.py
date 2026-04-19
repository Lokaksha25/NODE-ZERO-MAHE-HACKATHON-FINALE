from __future__ import annotations

from dataclasses import dataclass

from app.core.config import SEGMENT_LENGTH_METERS, WEAK_THRESHOLD, resolve_mode_weights
from app.core.models import (
    Coordinate,
    Operator,
    RankingMode,
    RouteResponse,
    SegmentResponse,
    WeakZoneResponse,
)
from app.data.demo_routes import RouteTemplate


@dataclass(frozen=True)
class ComputedRoute:
    response: RouteResponse


def _classify(score: float) -> str:
    if score < WEAK_THRESHOLD:
        return "weak"
    if score < 65:
        return "moderate"
    return "strong"


def _weak_zones(scores: list[float]) -> list[WeakZoneResponse]:
    zones: list[WeakZoneResponse] = []
    start = None
    for idx, score in enumerate(scores):
        weak = score < WEAK_THRESHOLD
        if weak and start is None:
            start = idx
        if not weak and start is not None:
            zones.append(
                WeakZoneResponse(
                    start_segment_index=start,
                    end_segment_index=idx - 1,
                    length_m=(idx - start) * SEGMENT_LENGTH_METERS,
                )
            )
            start = None
    if start is not None:
        zones.append(
            WeakZoneResponse(
                start_segment_index=start,
                end_segment_index=len(scores) - 1,
                length_m=(len(scores) - start) * SEGMENT_LENGTH_METERS,
            )
        )
    return zones


def _normalize_inverse(values: list[int]) -> list[float]:
    if not values:
        return []
    minimum = min(values)
    maximum = max(values)
    if maximum == minimum:
        return [100.0 for _ in values]
    return [100 * (maximum - value) / (maximum - minimum) for value in values]


def rank_routes(
    templates: list[RouteTemplate],
    operator: Operator,
    mode: RankingMode,
    blend: float,
    safety_mode: bool,
) -> list[RouteResponse]:
    if not templates:
        return []
    eta_scores = _normalize_inverse([template.eta_minutes for template in templates])
    weights = resolve_mode_weights(blend=blend, mode=mode.value, safety_mode=safety_mode)

    preliminary: list[dict[str, float | RouteTemplate | list[float] | list[SegmentResponse] | list[WeakZoneResponse]]] = []

    for template, eta_score in zip(templates, eta_scores):
        segment_scores = [segment.scores[operator] for segment in template.segments]
        segments = [
            SegmentResponse(
                index=idx,
                start=Coordinate(lon=segment.start_lon, lat=segment.start_lat),
                end=Coordinate(lon=segment.end_lon, lat=segment.end_lat),
                score=round(segment_score, 2),
                classification=_classify(segment_score),
            )
            for idx, (segment, segment_score) in enumerate(zip(template.segments, segment_scores))
        ]

        weak_zones = _weak_zones(segment_scores)
        weak_count = sum(1 for score in segment_scores if score < WEAK_THRESHOLD)
        weak_ratio = weak_count / len(segment_scores)
        longest_weak = max([zone.length_m for zone in weak_zones], default=0)
        connectivity_score = sum(segment_scores) / len(segment_scores)

        connectivity_rank_score = max(0.0, connectivity_score - weak_ratio * 22)
        raw_weak_penalty = weights.weak_penalty_weight * (
            (longest_weak / 1000.0) * 13 + weak_ratio * 35
        )
        # Scale penalty by connectivity weight so "fastest" mode doesn't get
        # overwhelmed by weak-zone penalties.  In safety mode the full penalty
        # applies regardless.
        penalty_scale = 1.0 if safety_mode else (0.3 + 0.7 * weights.connectivity_weight)
        weak_penalty = raw_weak_penalty * penalty_scale

        combined = (
            weights.eta_weight * eta_score
            + weights.connectivity_weight * connectivity_rank_score
            - weak_penalty
        )

        preliminary.append(
            {
                "template": template,
                "segment_scores": segment_scores,
                "segments": segments,
                "weak_zones": weak_zones,
                "eta_score": eta_score,
                "connectivity_score": connectivity_score,
                "min_segment_score": min(segment_scores),
                "weak_ratio": weak_ratio,
                "longest_weak": longest_weak,
                "connectivity_rank_score": connectivity_rank_score,
                "weak_penalty": weak_penalty,
                "combined": combined,
            }
        )

    best_route_id = max(preliminary, key=lambda item: item["combined"])["template"].route_id  # type: ignore[union-attr]

    responses: list[RouteResponse] = []
    for item in preliminary:
        template = item["template"]
        assert isinstance(template, RouteTemplate)
        responses.append(
            RouteResponse(
                route_id=template.route_id,
                label=template.label,
                distance_km=round(template.distance_km, 1),
                eta_minutes=template.eta_minutes,
                connectivity_score=round(float(item["connectivity_score"]), 2),
                minimum_segment_score=round(float(item["min_segment_score"]), 2),
                weak_segment_ratio=round(float(item["weak_ratio"]), 3),
                longest_weak_stretch_m=int(item["longest_weak"]),
                weak_zones=item["weak_zones"],  # type: ignore[arg-type]
                eta_score=round(float(item["eta_score"]), 2),
                connectivity_rank_score=round(float(item["connectivity_rank_score"]), 2),
                weak_penalty=round(float(item["weak_penalty"]), 2),
                combined_score=round(float(item["combined"]), 2),
                is_recommended=template.route_id == best_route_id,
                geometry=[
                    Coordinate(lon=lon, lat=lat)
                    for lon, lat in template.geometry
                ],
                segments=item["segments"],  # type: ignore[arg-type]
            )
        )

    responses.sort(key=lambda route: route.combined_score, reverse=True)
    return responses
