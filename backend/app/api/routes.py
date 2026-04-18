from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.core.config import SEGMENT_LENGTH_METERS, WARNING_LOOKAHEAD_METERS
from app.core.models import (
    Operator,
    PlaybackRequest,
    PlaybackResponse,
    PlaybackStep,
    RouteRequest,
    RoutesResponse,
    WeakZoneWarning,
)
from app.core.notification_engine import (
    build_seed_queue,
    evaluate_queue_at_segment,
    snapshot_pending,
)
from app.core.scoring import rank_routes
from app.data.demo_routes import get_demo_routes

router = APIRouter(prefix="/api", tags=["connectivity-demo"])


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/routes", response_model=RoutesResponse)
def get_ranked_routes(payload: RouteRequest) -> RoutesResponse:
    templates = get_demo_routes()
    ranked = rank_routes(
        templates=templates,
        operator=payload.operator,
        mode=payload.mode,
        blend=payload.eta_connectivity_blend,
        safety_mode=payload.safety_mode,
    )

    recommended = next((route.route_id for route in ranked if route.is_recommended), ranked[0].route_id)

    return RoutesResponse(
        selected_operator=payload.operator,
        mode=payload.mode,
        safety_mode=payload.safety_mode,
        eta_connectivity_blend=payload.eta_connectivity_blend,
        recommended_route_id=recommended,
        routes=ranked,
    )


@router.post("/playback", response_model=PlaybackResponse)
def simulate_playback(payload: PlaybackRequest) -> PlaybackResponse:
    templates = get_demo_routes()
    ranked_routes = rank_routes(
        templates=templates,
        operator=payload.operator,
        mode=payload.mode,
        blend=payload.eta_connectivity_blend,
        safety_mode=payload.safety_mode,
    )
    route_map = {route.route_id: route for route in ranked_routes}

    if payload.route_id not in route_map:
        raise HTTPException(status_code=404, detail=f"Unknown route_id: {payload.route_id}")

    selected = route_map[payload.route_id]
    better = ranked_routes[0]

    warning = _build_warning(selected, better, payload.mode)

    active_route = selected
    switched = False

    if warning and payload.decision_at_warning == "switch" and better.route_id != selected.route_id:
        active_route = better
        switched = True

    queue = build_seed_queue()
    steps: list[PlaybackStep] = []
    delivered = []
    consecutive_strong_meters = 0

    for segment in active_route.segments:
        if segment.classification == "strong":
            consecutive_strong_meters += SEGMENT_LENGTH_METERS
        else:
            consecutive_strong_meters = 0

        at_destination = segment.index == len(active_route.segments) - 1

        events = evaluate_queue_at_segment(
            queue=queue,
            segment_index=segment.index,
            segment_score=segment.score,
            consecutive_strong_meters=consecutive_strong_meters,
            at_destination=at_destination,
            safety_mode=payload.safety_mode,
        )
        delivered.extend(events)

        step_warning = warning if warning and segment.index == warning.at_segment_index and not switched else None
        steps.append(
            PlaybackStep(
                segment_index=segment.index,
                route_id=active_route.route_id,
                segment_score=segment.score,
                classification=segment.classification,
                notification_events=events,
                warning=step_warning,
            )
        )

    pending = snapshot_pending(queue)

    return PlaybackResponse(
        initial_route_id=selected.route_id,
        final_route_id=active_route.route_id,
        switched_route=switched,
        steps=steps,
        delivered_notifications=delivered,
        pending_notifications=pending,
    )


def _build_warning(
    selected_route,
    best_route,
    mode,
):
    if not selected_route.weak_zones:
        return None

    first_weak = selected_route.weak_zones[0]
    if first_weak.start_segment_index <= 1:
        warning_segment_index = 0
    else:
        lookahead_segments = WARNING_LOOKAHEAD_METERS // SEGMENT_LENGTH_METERS
        warning_segment_index = max(0, first_weak.start_segment_index - lookahead_segments)

    return WeakZoneWarning(
        at_segment_index=warning_segment_index,
        distance_to_weak_zone_m=(first_weak.start_segment_index - warning_segment_index) * SEGMENT_LENGTH_METERS,
        estimated_weak_zone_length_m=first_weak.length_m,
        current_mode=mode,
        better_connected_route_id=best_route.route_id,
    )
