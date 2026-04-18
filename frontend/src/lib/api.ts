import {
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

export async function fetchRoutes(payload: {
  operator: Operator;
  mode: RankingMode;
  eta_connectivity_blend: number;
  safety_mode: boolean;
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
}): Promise<PlaybackResponse> {
  return request<PlaybackResponse>("/playback", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
