from __future__ import annotations

from dataclasses import dataclass


SEGMENT_LENGTH_METERS = 100
WEAK_THRESHOLD = 45.0
STRONG_THRESHOLD = 65.0
LONG_STRONG_STRETCH_METERS = 500
WARNING_LOOKAHEAD_METERS = 700

OPERATOR_MNC_MAP = {
    "jio": ["405-86", "405-87"],
    "airtel": ["404-10", "404-49"],
}


@dataclass(frozen=True)
class ModeWeights:
    eta_weight: float
    connectivity_weight: float
    weak_penalty_weight: float


def resolve_mode_weights(
    blend: float,
    mode: str,
    safety_mode: bool,
) -> ModeWeights:
    clamped_blend = max(0.0, min(1.0, blend))

    eta_weight = 1.0 - clamped_blend
    connectivity_weight = clamped_blend
    weak_penalty_weight = 0.8

    if safety_mode:
        eta_weight *= 0.75
        connectivity_weight = min(1.0, connectivity_weight + 0.2)
        weak_penalty_weight = 1.3

    total = eta_weight + connectivity_weight
    if total == 0:
        return ModeWeights(0.5, 0.5, weak_penalty_weight)

    return ModeWeights(
        eta_weight / total, connectivity_weight / total, weak_penalty_weight
    )
