from __future__ import annotations

from dataclasses import dataclass

from app.core.config import LONG_STRONG_STRETCH_METERS, SEGMENT_LENGTH_METERS, STRONG_THRESHOLD
from app.core.models import NotificationEvent, NotificationPriority, NotificationState


@dataclass
class QueueItem:
    id: str
    title: str
    priority: NotificationPriority
    state: NotificationState = NotificationState.queued
    released_at_segment: int | None = None
    release_reason: str = ""


def build_seed_queue() -> list[QueueItem]:
    return [
        QueueItem(id="n-001", title="Emergency contact ping", priority=NotificationPriority.urgent),
        QueueItem(id="n-002", title="Ride OTP reminder", priority=NotificationPriority.semi_urgent),
        QueueItem(id="n-003", title="Offer from food app", priority=NotificationPriority.non_urgent),
    ]


def _to_event(item: QueueItem) -> NotificationEvent:
    return NotificationEvent(
        id=item.id,
        title=item.title,
        priority=item.priority,
        state=item.state,
        release_reason=item.release_reason,
        released_at_segment=item.released_at_segment,
    )


def evaluate_queue_at_segment(
    queue: list[QueueItem],
    segment_index: int,
    segment_score: float,
    consecutive_strong_meters: int,
    at_destination: bool,
    safety_mode: bool,
) -> list[NotificationEvent]:
    emitted: list[NotificationEvent] = []

    for item in queue:
        if item.state == NotificationState.delivered:
            continue

        if item.priority == NotificationPriority.urgent:
            item.state = NotificationState.delivered
            item.released_at_segment = segment_index
            item.release_reason = "bypassed because urgent"
            emitted.append(_to_event(item))
            continue

        if item.priority == NotificationPriority.semi_urgent:
            if segment_score >= STRONG_THRESHOLD:
                item.state = NotificationState.delivered
                item.released_at_segment = segment_index
                item.release_reason = "released on entering strong coverage zone"
                emitted.append(_to_event(item))
            else:
                item.state = NotificationState.deferred
            continue

        if item.priority == NotificationPriority.non_urgent:
            should_release = False
            reason = ""
            if not safety_mode and consecutive_strong_meters >= LONG_STRONG_STRETCH_METERS:
                should_release = True
                reason = "released on entering strong coverage zone"
            if at_destination:
                should_release = True
                reason = "released at destination"

            if should_release:
                item.state = NotificationState.delivered
                item.released_at_segment = segment_index
                item.release_reason = reason
                emitted.append(_to_event(item))
            else:
                item.state = NotificationState.deferred

    return emitted


def snapshot_pending(queue: list[QueueItem]) -> list[NotificationEvent]:
    return [_to_event(item) for item in queue if item.state != NotificationState.delivered]
