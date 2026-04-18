"use client";

import dynamic from "next/dynamic";
import { useEffect, useMemo, useRef, useState } from "react";

import { ControlPanel } from "@/components/control-panel";
import { Timeline } from "@/components/timeline";
import {
  createCorridorJob,
  fetchCorridorJob,
  fetchDataSourceStatus,
  fetchDataSourceStatusByCorridor,
  fetchPlayback,
  fetchRoutes,
} from "@/lib/api";
import {
  CorridorJobResponse,
  DataSourceStatus,
  Operator,
  PlaybackResponse,
  RankingMode,
  Route,
  RoutesResponse,
} from "@/types/api";

const MapView = dynamic(
  () => import("@/components/map-view").then((mod) => mod.MapView),
  { ssr: false },
);

function formatCorridorName(corridor: string | undefined) {
  if (!corridor) {
    return "Unknown corridor";
  }

  return corridor
    .split("-")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function routeSparkline(route: Route) {
  const total = Math.max(route.segments.length, 1);
  let weak = 0;
  let moderate = 0;
  let strong = 0;

  route.segments.forEach((segment) => {
    if (segment.classification === "weak") {
      weak += 1;
      return;
    }
    if (segment.classification === "moderate") {
      moderate += 1;
      return;
    }
    strong += 1;
  });

  return {
    weak: (weak / total) * 100,
    moderate: (moderate / total) * 100,
    strong: (strong / total) * 100,
  };
}

export default function Home() {
  const [sourceCity, setSourceCity] = useState<string>("Oslo");
  const [destinationCity, setDestinationCity] = useState<string>("Drammen");
  const [sourceTouched, setSourceTouched] = useState<boolean>(false);
  const [destinationTouched, setDestinationTouched] = useState<boolean>(false);
  const [activeCorridorId, setActiveCorridorId] = useState<string | null>(null);
  const [job, setJob] = useState<CorridorJobResponse | null>(null);
  const [buildingCorridor, setBuildingCorridor] = useState<boolean>(false);

  const [operator, setOperator] = useState<Operator>("jio");
  const [mode, setMode] = useState<RankingMode>("fastest");
  const [blend, setBlend] = useState<number>(0.5);
  const [safetyMode, setSafetyMode] = useState<boolean>(false);
  const [playbackDecision, setPlaybackDecision] = useState<"continue" | "switch">("continue");
  const [theme, setTheme] = useState<"light" | "dark">("light");

  const [routesResponse, setRoutesResponse] = useState<RoutesResponse | null>(null);
  const [dataSource, setDataSource] = useState<DataSourceStatus | null>(null);
  const [selectedRouteId, setSelectedRouteId] = useState<string>("");
  const [loadingRoutes, setLoadingRoutes] = useState<boolean>(false);

  const [playback, setPlayback] = useState<PlaybackResponse | null>(null);
  const [playbackIndex, setPlaybackIndex] = useState<number>(-1);
  const [loadingPlayback, setLoadingPlayback] = useState<boolean>(false);

  const [error, setError] = useState<string>("");
  const lastRankingKeyRef = useRef<string>("");

  useEffect(() => {
    const stored = window.localStorage.getItem("corridor-theme");
    if (stored === "light" || stored === "dark") {
      setTheme(stored);
    }
  }, []);

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    if (theme === "dark") {
      document.documentElement.classList.add("dark");
    } else {
      document.documentElement.classList.remove("dark");
    }
    window.localStorage.setItem("corridor-theme", theme);
  }, [theme]);

  useEffect(() => {
    let isMounted = true;

    const load = activeCorridorId
      ? fetchDataSourceStatusByCorridor(activeCorridorId)
      : fetchDataSourceStatus();

    load
      .then((status) => {
        if (!isMounted) {
          return;
        }
        setDataSource(status);
      })
      .catch(() => {
        if (!isMounted) {
          return;
        }
        setDataSource(null);
      });

    return () => {
      isMounted = false;
    };
  }, [activeCorridorId]);

  useEffect(() => {
    if (!dataSource?.corridor || sourceTouched || destinationTouched) {
      return;
    }

    const parts = dataSource.corridor
      .split("-")
      .map((part) => part.trim())
      .filter(Boolean);

    if (parts.length >= 2) {
      const from = parts[0].charAt(0).toUpperCase() + parts[0].slice(1);
      const to = parts[parts.length - 1].charAt(0).toUpperCase() + parts[parts.length - 1].slice(1);
      setSourceCity(from);
      setDestinationCity(to);
    }
  }, [dataSource?.corridor, sourceTouched, destinationTouched]);

  useEffect(() => {
    let isMounted = true;
    const rankingKey = `${operator}:${mode}:${blend}:${safetyMode}`;
    setLoadingRoutes(true);
    setError("");

    fetchRoutes({
      operator,
      mode,
      eta_connectivity_blend: blend,
      safety_mode: safetyMode,
      corridor_id: activeCorridorId ?? undefined,
    })
      .then((data) => {
        if (!isMounted) {
          return;
        }
        setRoutesResponse(data);
        const fallback = data.recommended_route_id;
        const rankingChanged = lastRankingKeyRef.current !== rankingKey;
        lastRankingKeyRef.current = rankingKey;

        setSelectedRouteId((current) => {
          const exists = data.routes.some((route) => route.route_id === current);
          if (!exists || rankingChanged) {
            return fallback;
          }
          return current;
        });
      })
      .catch((err) => {
        if (!isMounted) {
          return;
        }
        setError(String(err));
      })
      .finally(() => {
        if (isMounted) {
          setLoadingRoutes(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [operator, mode, blend, safetyMode, activeCorridorId]);

  useEffect(() => {
    if (!playback || playback.steps.length === 0) {
      return;
    }

    setPlaybackIndex(0);

    const timer = window.setInterval(() => {
      setPlaybackIndex((current) => {
        if (current >= playback.steps.length - 1) {
          window.clearInterval(timer);
          return current;
        }
        return current + 1;
      });
    }, 850);

    return () => {
      window.clearInterval(timer);
    };
  }, [playback]);

  const routes = routesResponse?.routes ?? [];
  const corridorName = formatCorridorName(dataSource?.corridor);
  const operatorLabels = dataSource?.operator_labels ?? {
    jio: "Jio",
    airtel: "Airtel",
  };
  const operatorNote = dataSource?.operator_note ?? undefined;

  const selectedRoute = useMemo<Route | null>(() => {
    if (!routes.length) {
      return null;
    }
    return routes.find((route) => route.route_id === selectedRouteId) ?? routes[0];
  }, [routes, selectedRouteId]);

  const activeStep =
    playback && playbackIndex >= 0 && playbackIndex < playback.steps.length
      ? playback.steps[playbackIndex]
      : null;

  const mapActiveRouteId = activeStep?.route_id ?? selectedRouteId;
  const playbackSegmentIndex = activeStep?.segment_index ?? -1;

  async function runPlayback(decision: "continue" | "switch") {
    if (!selectedRoute) {
      return;
    }
    setLoadingPlayback(true);
    setError("");
    try {
      const response = await fetchPlayback({
        operator,
        route_id: selectedRoute.route_id,
        mode,
        eta_connectivity_blend: blend,
        safety_mode: safetyMode,
        decision_at_warning: decision,
        corridor_id: activeCorridorId ?? undefined,
      });
      setPlayback(response);
      setPlaybackIndex(-1);
      if (response.switched_route) {
        setSelectedRouteId(response.final_route_id);
      }
    } catch (err) {
      setError(String(err));
    } finally {
      setLoadingPlayback(false);
    }
  }

  async function pollCorridor(jobId: string) {
    const timer = window.setInterval(async () => {
      try {
        const latest = await fetchCorridorJob(jobId);
        setJob(latest);

        if (latest.status === "failed") {
          window.clearInterval(timer);
          setBuildingCorridor(false);
          setError(latest.error ?? "Corridor task failed.");
          return;
        }

        if (latest.status === "ready" || latest.status === "ready_degraded") {
          window.clearInterval(timer);
          setBuildingCorridor(false);
          setActiveCorridorId(latest.corridor_id);
        }
      } catch (pollError) {
        window.clearInterval(timer);
        setBuildingCorridor(false);
        setError(String(pollError));
      }
    }, 2000);
  }

  async function onBuildCorridor(forceRefresh: boolean) {
    if (!sourceCity.trim() || !destinationCity.trim()) {
      setError("Please enter both source and destination cities.");
      return;
    }

    setError("");
    setBuildingCorridor(true);

    try {
      const created = await createCorridorJob({
        source_city: sourceCity.trim(),
        destination_city: destinationCity.trim(),
        force_refresh: forceRefresh,
      });
      setJob(created);

      if (created.status === "ready" || created.status === "ready_degraded") {
        setActiveCorridorId(created.corridor_id);
        setBuildingCorridor(false);
        return;
      }

      await pollCorridor(created.job_id);
    } catch (buildError) {
      setBuildingCorridor(false);
      setError(String(buildError));
    }
  }

  const sourceLabel = job?.source_label ?? sourceCity;
  const destinationLabel = job?.destination_label ?? destinationCity;

  return (
    <main className="relative min-h-[100dvh] w-screen overflow-x-hidden bg-[var(--surface)] text-[var(--text-primary)]">
      <MapView
        routes={routes}
        selectedRouteId={mapActiveRouteId}
        playbackSegmentIndex={playbackSegmentIndex}
        startLabel={sourceLabel}
        endLabel={destinationLabel}
        theme={theme}
      />

      <section className="pointer-events-none relative z-10 flex min-h-[100dvh] flex-col overflow-y-auto px-4 pb-4 pt-4 sm:px-8 sm:pb-7 sm:pt-7">
        <div className="pointer-events-auto flex items-start justify-between gap-3">
          <div className="floating-card flex w-full max-w-[760px] flex-wrap items-center gap-3 rounded-2xl px-4 py-3 sm:px-6 sm:py-4">
            <div className="min-w-[170px] flex-1">
              <p className="text-sm text-[var(--text-muted)]">Origin</p>
              <input
                value={sourceCity}
                onChange={(event) => {
                  setSourceTouched(true);
                  setSourceCity(event.target.value);
                }}
                className="w-full bg-transparent text-2xl font-extrabold leading-none tracking-tight outline-none sm:text-3xl"
              />
            </div>

            <div className="flex h-10 w-10 items-center justify-center rounded-full border border-[var(--border)] bg-[var(--card-elevated)] text-xl font-bold">
              -&gt;
            </div>

            <div className="min-w-[170px] flex-1">
              <p className="text-sm text-[var(--text-muted)]">Destination</p>
              <input
                value={destinationCity}
                onChange={(event) => {
                  setDestinationTouched(true);
                  setDestinationCity(event.target.value);
                }}
                className="w-full bg-transparent text-2xl font-extrabold leading-none tracking-tight outline-none sm:text-3xl"
              />
            </div>

            <div className="flex items-center gap-2">
              <span className="text-base font-medium">{theme === "light" ? "Light" : "Dark"}</span>
              <button
                type="button"
                onClick={() => setTheme((current) => (current === "light" ? "dark" : "light"))}
                className={`theme-toggle ${theme === "dark" ? "is-dark" : ""}`}
                aria-label="Toggle theme"
                aria-pressed={theme === "dark"}
              >
                <span className="theme-toggle-knob" />
              </button>
            </div>
          </div>

        </div>

        <div className="pointer-events-auto mt-4 flex gap-3">
          <button
            type="button"
            disabled={buildingCorridor}
            onClick={() => onBuildCorridor(false)}
            className="rounded-xl border border-[var(--border)] bg-[var(--card)] px-3 py-2 text-sm font-semibold shadow-sm transition hover:border-[var(--text-muted)] disabled:cursor-not-allowed disabled:opacity-60"
          >
            {buildingCorridor ? "Building..." : "Build Corridor"}
          </button>
          <button
            type="button"
            disabled={buildingCorridor}
            onClick={() => onBuildCorridor(true)}
            className="rounded-xl border border-[var(--border)] bg-[var(--card)] px-3 py-2 text-sm font-semibold shadow-sm transition hover:border-[var(--text-muted)] disabled:cursor-not-allowed disabled:opacity-60"
          >
            {buildingCorridor ? "Refreshing..." : "Refresh Data"}
          </button>
          {dataSource ? (
            <div className="hidden items-center rounded-xl border border-[var(--border)] bg-[var(--card)] px-3 py-2 text-xs text-[var(--text-muted)] lg:flex">
              {corridorName} | {dataSource.source_mode === "cached" ? "Cached OSRM+OpenCellID" : "Fallback Synthetic"}
            </div>
          ) : null}
        </div>

        {job ? (
          <div className="pointer-events-auto mt-2 inline-flex rounded-xl border border-[var(--border)] bg-[var(--card)] px-3 py-2 text-xs text-[var(--text-muted)]">
            Job {job.job_id} | {job.stage} | {job.progress_pct}% | {job.status}
            {job.degraded && job.degraded_reason ? ` | ${job.degraded_reason}` : ""}
          </div>
        ) : null}

        {error ? (
          <div className="pointer-events-auto mt-2 inline-flex rounded-xl border border-red-500/60 bg-red-500/10 px-3 py-2 text-xs text-red-600 dark:text-red-300">
            {error}
          </div>
        ) : null}

        <div className="pointer-events-auto mt-5 flex-1">
          <div onWheelCapture={(event) => event.stopPropagation()}>
            <ControlPanel
              operator={operator}
              operatorLabels={operatorLabels}
              operatorNote={operatorNote}
              mode={mode}
              blend={blend}
              safetyMode={safetyMode}
              playbackDecision={playbackDecision}
              routes={routes}
              selectedRouteId={selectedRouteId}
              loading={loadingRoutes || loadingPlayback}
              onOperatorChange={setOperator}
              onModeChange={setMode}
              onBlendChange={setBlend}
              onSafetyModeChange={setSafetyMode}
              onPlaybackDecisionChange={setPlaybackDecision}
              onSelectRoute={setSelectedRouteId}
              theme={theme}
            />
          </div>
        </div>

        <div className="pointer-events-auto mt-auto grid grid-cols-1 gap-4 lg:grid-cols-[minmax(0,1fr)_470px]">
          <div>
            <div className="hide-scrollbar overflow-x-auto pb-2">
              <div className="flex min-w-max gap-3">
                {routes.map((route) => {
                  const spark = routeSparkline(route);
                  const selected = route.route_id === selectedRouteId;

                  return (
                    <button
                      type="button"
                      key={route.route_id}
                      onClick={() => setSelectedRouteId(route.route_id)}
                      className={`floating-card min-w-[250px] rounded-2xl p-4 text-left transition ${
                        selected ? "border-2 border-black dark:border-white" : "border border-[var(--border)]"
                      }`}
                    >
                      <div className="mb-1 flex items-center justify-between">
                        <p className="text-base font-extrabold leading-tight tracking-tight">{route.label}</p>
                        {route.is_recommended ? (
                          <span className="rounded-full bg-emerald-500/15 px-2 py-1 text-[10px] font-bold uppercase tracking-widest text-emerald-600 dark:text-emerald-300">
                            Recommended
                          </span>
                        ) : null}
                      </div>

                      <p className="text-sm text-[var(--text-muted)]">Score: <span className="text-[var(--text-primary)]">{route.connectivity_score}</span></p>
                      <p className="mb-2 text-sm text-[var(--text-muted)]">ETA: <span className="text-[var(--text-primary)]">{route.eta_minutes} min</span></p>

                      <div className="overflow-hidden rounded-full border border-black/10 bg-black/5 dark:border-white/20 dark:bg-white/10">
                        <div className="flex h-2 w-full">
                          <div className="bg-[#2d965d]" style={{ width: `${spark.strong}%` }} />
                          <div className="bg-[#e3a008]" style={{ width: `${spark.moderate}%` }} />
                          <div className="bg-[#e14c4c]" style={{ width: `${spark.weak}%` }} />
                        </div>
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>

            <button
              type="button"
              disabled={loadingRoutes || loadingPlayback || !selectedRoute}
              onClick={() => runPlayback(playbackDecision)}
              className="mt-3 w-full rounded-xl bg-black px-4 py-3 text-4xl font-extrabold leading-none tracking-tight text-white shadow-lg transition hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-60 dark:bg-white dark:text-black"
            >
              Analyze
            </button>
          </div>

          <div className="space-y-3">
            <section className="floating-card rounded-2xl px-5 py-5">
              <h2 className="text-[38px] font-extrabold leading-none tracking-tight">Selected Route Insight</h2>
              {selectedRoute ? (
                <div className="mt-4 grid grid-cols-2 gap-3 text-sm sm:grid-cols-4">
                  <div>
                    <p className="text-xs uppercase tracking-wide text-[var(--text-muted)]">ETA</p>
                    <p className="text-3xl font-bold">{selectedRoute.eta_minutes} min</p>
                  </div>
                  <div>
                    <p className="text-xs uppercase tracking-wide text-[var(--text-muted)]">Distance</p>
                    <p className="text-3xl font-bold">{selectedRoute.distance_km} km</p>
                  </div>
                  <div>
                    <p className="text-xs uppercase tracking-wide text-[var(--text-muted)]">Connectivity</p>
                    <p className="text-3xl font-bold">{selectedRoute.connectivity_score}</p>
                  </div>
                  <div>
                    <p className="text-xs uppercase tracking-wide text-[var(--text-muted)]">Longest Weak Stretch</p>
                    <p className="text-3xl font-bold">{selectedRoute.longest_weak_stretch_m} m</p>
                  </div>
                </div>
              ) : (
                <p className="mt-3 text-sm text-[var(--text-muted)]">Loading route intelligence...</p>
              )}
            </section>

            {playback ? (
              <div className="max-h-[280px] overflow-auto rounded-2xl">
                <Timeline playback={playback} activeStep={activeStep} />
              </div>
            ) : null}
          </div>
        </div>
      </section>
    </main>
  );
}
