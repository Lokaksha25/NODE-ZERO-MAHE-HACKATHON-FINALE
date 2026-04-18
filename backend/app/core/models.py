from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class Operator(str, Enum):
    jio = "jio"
    airtel = "airtel"


class RankingMode(str, Enum):
    fastest = "fastest"
    most_connected = "most_connected"


class NotificationPriority(str, Enum):
    urgent = "urgent"
    semi_urgent = "semi-urgent"
    non_urgent = "non-urgent"


class NotificationState(str, Enum):
    queued = "queued"
    deferred = "deferred"
    released = "released"
    delivered = "delivered"


class RouteRequest(BaseModel):
    operator: Operator
    mode: RankingMode = RankingMode.fastest
    eta_connectivity_blend: float = Field(default=0.5, ge=0.0, le=1.0)
    safety_mode: bool = False


class Coordinate(BaseModel):
    lon: float
    lat: float


class SegmentResponse(BaseModel):
    index: int
    start: Coordinate
    end: Coordinate
    score: float
    classification: Literal["weak", "moderate", "strong"]


class WeakZoneResponse(BaseModel):
    start_segment_index: int
    end_segment_index: int
    length_m: int


class RouteResponse(BaseModel):
    route_id: str
    label: str
    distance_km: float
    eta_minutes: int
    connectivity_score: float
    minimum_segment_score: float
    weak_segment_ratio: float
    longest_weak_stretch_m: int
    weak_zones: list[WeakZoneResponse]
    eta_score: float
    connectivity_rank_score: float
    weak_penalty: float
    combined_score: float
    is_recommended: bool
    geometry: list[Coordinate]
    segments: list[SegmentResponse]


class RoutesResponse(BaseModel):
    selected_operator: Operator
    mode: RankingMode
    safety_mode: bool
    eta_connectivity_blend: float
    recommended_route_id: str
    routes: list[RouteResponse]


class DataSourceStatus(BaseModel):
    source_mode: Literal["cached", "fallback"]
    source_name: str
    cache_exists: bool
    route_count: int
    tower_count: int
    generated_at: int


class NotificationEvent(BaseModel):
    id: str
    title: str
    priority: NotificationPriority
    state: NotificationState
    release_reason: str
    released_at_segment: int | None = None


class PlaybackRequest(BaseModel):
    operator: Operator
    route_id: str
    mode: RankingMode = RankingMode.fastest
    eta_connectivity_blend: float = Field(default=0.5, ge=0.0, le=1.0)
    safety_mode: bool = False
    decision_at_warning: Literal["continue", "switch"] = "continue"


class WeakZoneWarning(BaseModel):
    at_segment_index: int
    distance_to_weak_zone_m: int
    estimated_weak_zone_length_m: int
    current_mode: RankingMode
    better_connected_route_id: str


class PlaybackStep(BaseModel):
    segment_index: int
    route_id: str
    segment_score: float
    classification: Literal["weak", "moderate", "strong"]
    notification_events: list[NotificationEvent]
    warning: WeakZoneWarning | None = None


class PlaybackResponse(BaseModel):
    initial_route_id: str
    final_route_id: str
    switched_route: bool
    steps: list[PlaybackStep]
    delivered_notifications: list[NotificationEvent]
    pending_notifications: list[NotificationEvent]
