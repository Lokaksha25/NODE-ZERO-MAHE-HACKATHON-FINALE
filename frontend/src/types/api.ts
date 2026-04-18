export type Operator = "jio" | "airtel";
export type RankingMode = "fastest" | "most_connected";

export type SegmentClass = "weak" | "moderate" | "strong";

export interface Coordinate {
  lon: number;
  lat: number;
}

export interface Segment {
  index: number;
  start: Coordinate;
  end: Coordinate;
  score: number;
  classification: SegmentClass;
}

export interface WeakZone {
  start_segment_index: number;
  end_segment_index: number;
  length_m: number;
}

export interface Route {
  route_id: string;
  label: string;
  distance_km: number;
  eta_minutes: number;
  connectivity_score: number;
  minimum_segment_score: number;
  weak_segment_ratio: number;
  longest_weak_stretch_m: number;
  weak_zones: WeakZone[];
  eta_score: number;
  connectivity_rank_score: number;
  weak_penalty: number;
  combined_score: number;
  is_recommended: boolean;
  geometry: Coordinate[];
  segments: Segment[];
}

export interface RoutesResponse {
  selected_operator: Operator;
  mode: RankingMode;
  safety_mode: boolean;
  eta_connectivity_blend: number;
  recommended_route_id: string;
  routes: Route[];
}

export type NotificationPriority = "urgent" | "semi-urgent" | "non-urgent";
export type NotificationState = "queued" | "deferred" | "released" | "delivered";

export interface NotificationEvent {
  id: string;
  title: string;
  priority: NotificationPriority;
  state: NotificationState;
  release_reason: string;
  released_at_segment: number | null;
}

export interface WeakZoneWarning {
  at_segment_index: number;
  distance_to_weak_zone_m: number;
  estimated_weak_zone_length_m: number;
  current_mode: RankingMode;
  better_connected_route_id: string;
}

export interface PlaybackStep {
  segment_index: number;
  route_id: string;
  segment_score: number;
  classification: SegmentClass;
  notification_events: NotificationEvent[];
  warning: WeakZoneWarning | null;
}

export interface PlaybackResponse {
  initial_route_id: string;
  final_route_id: string;
  switched_route: boolean;
  steps: PlaybackStep[];
  delivered_notifications: NotificationEvent[];
  pending_notifications: NotificationEvent[];
}
