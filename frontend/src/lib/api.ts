import {
  CorridorJobResponse,
  DataSourceStatus,
  PlaybackResponse,
  RankingMode,
  RoutesResponse,
  Operator,
} from "@/types/api";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000/api";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    cache: "no-store",
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(`API ${path} failed: ${response.status} ${text}`);
  }

  return response.json() as Promise<T>;
}

export async function fetchDataSourceStatus(): Promise<DataSourceStatus> {
  return request<DataSourceStatus>("/data-source", {
    method: "GET",
  });
}

export async function fetchDataSourceStatusByCorridor(
  corridorId: string,
): Promise<DataSourceStatus> {
  const query = new URLSearchParams({ corridor_id: corridorId });
  return request<DataSourceStatus>(`/data-source?${query.toString()}`, {
    method: "GET",
  });
}

export async function createCorridorJob(payload: {
  source_city: string;
  destination_city: string;
  force_refresh?: boolean;
}): Promise<CorridorJobResponse> {
  return request<CorridorJobResponse>("/corridor-jobs", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function fetchCorridorJob(jobId: string): Promise<CorridorJobResponse> {
  return request<CorridorJobResponse>(`/corridor-jobs/${jobId}`, {
    method: "GET",
  });
}

export async function fetchRoutes(payload: {
  operator: Operator;
  mode: RankingMode;
  eta_connectivity_blend: number;
  safety_mode: boolean;
  corridor_id?: string;
}): Promise<RoutesResponse> {
  return request<RoutesResponse>("/routes", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function fetchPlayback(payload: {
  operator: Operator;
  route_id: string;
  mode: RankingMode;
  eta_connectivity_blend: number;
  safety_mode: boolean;
  decision_at_warning: "continue" | "switch";
  corridor_id?: string;
}): Promise<PlaybackResponse> {
  return request<PlaybackResponse>("/playback", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
