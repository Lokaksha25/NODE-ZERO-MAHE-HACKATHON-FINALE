from __future__ import annotations

from dataclasses import dataclass, field

from app.core.config import LONG_STRONG_STRETCH_METERS, SEGMENT_LENGTH_METERS, STRONG_THRESHOLD, WEAK_THRESHOLD


# ---------------------------------------------------------------------------
# Zone classification helpers
# ---------------------------------------------------------------------------

def classify_zone(score: float) -> str:
    """Classify a segment score into a connectivity zone.

    Returns:
        "strong"   – green zone  (score >= STRONG_THRESHOLD)
        "moderate"  – yellow zone (WEAK_THRESHOLD <= score < STRONG_THRESHOLD)
        "weak"      – red zone    (score < WEAK_THRESHOLD)
    """
    if score >= STRONG_THRESHOLD:
        return "strong"
    if score >= WEAK_THRESHOLD:
        return "moderate"
    return "weak"


# ---------------------------------------------------------------------------
# Stagger configuration
# ---------------------------------------------------------------------------

# Minimum segments of strong coverage before a semi-urgent notification is
# released.  Each subsequent semi-urgent notification needs an additional
# SEMI_STAGGER_SEGMENTS segments.
SEMI_STAGGER_SEGMENTS = 5

# Non-urgent notifications require even longer sustained coverage.  Each
# subsequent non-urgent notification adds this many extra segments on top
# of the LONG_STRONG_STRETCH_METERS base requirement.
NON_URGENT_EXTRA_STAGGER_SEGMENTS = 8


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class QueueItem:
    id: str
    title: str
    body: str
    priority: NotificationPriority
    state: NotificationState = field(default_factory=lambda: NotificationState.queued)
    released_at_segment: int | None = None
    release_reason: str = ""
    visible: bool = False  # whether the notification is visible to the user at the current step
    _stagger_rank: int = 0  # auto-assigned rank within priority tier for staggering


# We import these after the QueueItem definition to keep the file readable,
# but they are used inside QueueItem's type hints above. Python's
# ``from __future__ import annotations`` makes this safe.
from app.core.models import NotificationEvent, NotificationPriority, NotificationState  # noqa: E402


# ---------------------------------------------------------------------------
# Seed queue – a realistic set of notifications across all priority tiers
# ---------------------------------------------------------------------------

def build_seed_queue() -> list[QueueItem]:
    """Build the initial notification queue with a realistic mix of priorities.

    Priority distribution:
      - urgent (3)     – always delivered immediately regardless of zone
      - semi-urgent (3) – delivered in green/yellow zones, hidden in red
      - non-urgent (4)  – delivered only in sustained green zones or at destination
    """
    items = [
        # ── Urgent ──────────────────────────────────────────
        QueueItem(
            id="n-001",
            title="Emergency contact ping",
            body="Your emergency contact is trying to reach you.",
            priority=NotificationPriority.urgent,
        ),
        QueueItem(
            id="n-002",
            title="SOS alert from family",
            body="A family member triggered an SOS alert.",
            priority=NotificationPriority.urgent,
        ),
        QueueItem(
            id="n-003",
            title="Fraud alert – bank",
            body="Unusual transaction detected on your account.",
            priority=NotificationPriority.urgent,
        ),

        # ── Semi-urgent ─────────────────────────────────────
        QueueItem(
            id="n-004",
            title="Ride OTP reminder",
            body="Your ride-share verification code is 4829.",
            priority=NotificationPriority.semi_urgent,
        ),
        QueueItem(
            id="n-005",
            title="Meeting in 15 minutes",
            body="Standup with the team starts at 10:30 AM.",
            priority=NotificationPriority.semi_urgent,
        ),
        QueueItem(
            id="n-006",
            title="Package out for delivery",
            body="Your Flipkart order is arriving today.",
            priority=NotificationPriority.semi_urgent,
        ),

        # ── Non-urgent ──────────────────────────────────────
        QueueItem(
            id="n-007",
            title="Offer from food app",
            body="50% off on your next Swiggy order!",
            priority=NotificationPriority.non_urgent,
        ),
        QueueItem(
            id="n-008",
            title="News digest",
            body="Your morning briefing is ready.",
            priority=NotificationPriority.non_urgent,
        ),
        QueueItem(
            id="n-009",
            title="Social media update",
            body="3 people liked your photo.",
            priority=NotificationPriority.non_urgent,
        ),
        QueueItem(
            id="n-010",
            title="App update available",
            body="A new version of WhatsApp is available.",
            priority=NotificationPriority.non_urgent,
        ),
    ]

    # Auto-assign stagger ranks within each priority tier
    tier_counters: dict[str, int] = {}
    for item in items:
        tier = item.priority.value
        rank = tier_counters.get(tier, 0)
        item._stagger_rank = rank
        tier_counters[tier] = rank + 1

    return items


# ---------------------------------------------------------------------------
# Conversion helper
# ---------------------------------------------------------------------------

def _to_event(item: QueueItem) -> NotificationEvent:
    return NotificationEvent(
        id=item.id,
        title=item.title,
        priority=item.priority,
        state=item.state,
        release_reason=item.release_reason,
        released_at_segment=item.released_at_segment,
    )


# ---------------------------------------------------------------------------
# Core evaluation – called once per segment during playback
# ---------------------------------------------------------------------------

def evaluate_queue_at_segment(
    queue: list[QueueItem],
    segment_index: int,
    segment_score: float,
    consecutive_strong_meters: int,
    at_destination: bool,
    safety_mode: bool,
) -> list[NotificationEvent]:
    """Evaluate which notifications should be emitted at this segment.

    Zone-aware delivery rules (from the SPEC):
    ┌─────────────┬──────────────────────────────────────────────────────┐
    │  Zone        │  Delivery policy                                    │
    ├─────────────┼──────────────────────────────────────────────────────┤
    │  🟢 Strong   │  All priorities – released in controlled manner     │
    │  🟡 Moderate │  Urgent + semi-urgent only; non-urgent hidden       │
    │  🔴 Weak     │  Urgent only                                        │
    └─────────────┴──────────────────────────────────────────────────────┘

    "Controlled manner" means staggered release:
      - Semi-urgent: each subsequent item waits SEMI_STAGGER_SEGMENTS more
        segments of strong coverage.
      - Non-urgent: requires LONG_STRONG_STRETCH_METERS base, plus each
        subsequent item waits NON_URGENT_EXTRA_STAGGER_SEGMENTS more.
    """
    zone = classify_zone(segment_score)
    emitted: list[NotificationEvent] = []
    consecutive_strong_segments = consecutive_strong_meters // SEGMENT_LENGTH_METERS

    for item in queue:
        if item.state == NotificationState.delivered:
            # Already delivered – keep visible flag on
            item.visible = True
            continue

        # ── URGENT ──────────────────────────────────────────
        # Always delivered immediately, regardless of zone.
        if item.priority == NotificationPriority.urgent:
            if item.state != NotificationState.delivered:
                item.state = NotificationState.delivered
                item.released_at_segment = segment_index
                item.release_reason = "bypassed because urgent"
                item.visible = True
                emitted.append(_to_event(item))
            continue

        # ── SEMI-URGENT ─────────────────────────────────────
        # Visible in green and yellow zones.
        # Delivered when segment is strong (green), staggered by rank.
        # Deferred and hidden in red zones.
        if item.priority == NotificationPriority.semi_urgent:
            required_strong_segments = SEMI_STAGGER_SEGMENTS * (1 + item._stagger_rank)

            if zone == "weak":
                # Red zone – hide and defer
                item.state = NotificationState.deferred
                item.release_reason = "deferred due to weak connectivity"
                item.visible = False
            elif zone == "moderate":
                # Yellow zone – visible but not yet delivered (waiting for green)
                item.state = NotificationState.deferred
                item.release_reason = "waiting for stronger coverage"
                item.visible = True  # visible in yellow, just not released
            elif zone == "strong":
                # Green zone – deliver only after enough consecutive strong segments
                if consecutive_strong_segments >= required_strong_segments:
                    item.state = NotificationState.delivered
                    item.released_at_segment = segment_index
                    item.release_reason = "released on entering strong coverage zone"
                    item.visible = True
                    emitted.append(_to_event(item))
                else:
                    item.state = NotificationState.deferred
                    item.release_reason = "queued for controlled release"
                    item.visible = True

            # Destination fallback
            if at_destination and item.state != NotificationState.delivered:
                item.state = NotificationState.delivered
                item.released_at_segment = segment_index
                item.release_reason = "released at destination"
                item.visible = True
                emitted.append(_to_event(item))
            continue

        # ── NON-URGENT ──────────────────────────────────────
        # Only visible in green zones.
        # Requires sustained strong coverage or destination arrival.
        # Hidden in yellow and red zones.
        if item.priority == NotificationPriority.non_urgent:
            base_meters = LONG_STRONG_STRETCH_METERS
            extra_meters = NON_URGENT_EXTRA_STAGGER_SEGMENTS * SEGMENT_LENGTH_METERS * item._stagger_rank
            required_meters = base_meters + extra_meters

            if safety_mode:
                required_meters = int(required_meters * 2)

            if zone == "weak":
                item.state = NotificationState.deferred
                item.release_reason = "deferred due to weak connectivity"
                item.visible = False
            elif zone == "moderate":
                item.state = NotificationState.deferred
                item.release_reason = "deferred – moderate zone, waiting for strong coverage"
                item.visible = False  # hidden in yellow
            elif zone == "strong":
                # Green zone – visible, but only deliver after sustained coverage
                if consecutive_strong_meters >= required_meters:
                    item.state = NotificationState.delivered
                    item.released_at_segment = segment_index
                    item.release_reason = "released after sustained strong coverage"
                    item.visible = True
                    emitted.append(_to_event(item))
                else:
                    item.state = NotificationState.deferred
                    item.release_reason = "waiting for sustained strong coverage"
                    item.visible = True  # visible in green, but not yet delivered

            # Destination fallback – always release remaining at destination
            if at_destination and item.state != NotificationState.delivered:
                item.state = NotificationState.delivered
                item.released_at_segment = segment_index
                item.release_reason = "released at destination"
                item.visible = True
                emitted.append(_to_event(item))

    return emitted


# ---------------------------------------------------------------------------
# Snapshot helpers for the playback response
# ---------------------------------------------------------------------------

def snapshot_pending(queue: list[QueueItem]) -> list[NotificationEvent]:
    """Return events for items that have NOT yet been delivered."""
    return [_to_event(item) for item in queue if item.state != NotificationState.delivered]


def snapshot_visible(queue: list[QueueItem]) -> list[NotificationEvent]:
    """Return events for items that are currently visible to the user.

    This is the key function the frontend uses to decide what to render
    at the current playback step. It respects zone-based visibility rules.
    """
    return [_to_event(item) for item in queue if item.visible]
