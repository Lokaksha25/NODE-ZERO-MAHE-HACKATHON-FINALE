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
  if (!corridor) return "Unknown corridor";
  return corridor
    .split("-")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

export default function Home() {
  const [sourceCity, setSourceCity] = useState<string>("");
  const [destinationCity, setDestinationCity] = useState<string>("");
  const [sourceTouched, setSourceTouched] = useState<boolean>(false);
  const [destinationTouched, setDestinationTouched] = useState<boolean>(false);
  const [activeCorridorId, setActiveCorridorId] = useState<string | null>(null);
  const [job, setJob] = useState<CorridorJobResponse | null>(null);
  const [buildingCorridor, setBuildingCorridor] = useState<boolean>(false);

  const [operator, setOperator] = useState<Operator>("jio");
  const [mode, setMode] = useState<RankingMode>("fastest");
  const [blend, setBlend] = useState<number>(0.15);
  function handleModeChange(newMode: RankingMode) {
    setMode(newMode);
    setBlend(newMode === "fastest" ? 0.15 : 0.85);
  }
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
    if (stored === "light" || stored === "dark") setTheme(stored);
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
    if (!activeCorridorId) return;
    let isMounted = true;
    const load = fetchDataSourceStatusByCorridor(activeCorridorId);

    load
      .then((status) => { if (isMounted) setDataSource(status); })
      .catch(() => { if (isMounted) setDataSource(null); });

    return () => { isMounted = false; };
  }, [activeCorridorId]);

  useEffect(() => {
    if (!dataSource?.corridor || sourceTouched || destinationTouched) return;
    const parts = dataSource.corridor.split("-").map((p) => p.trim()).filter(Boolean);
    if (parts.length >= 2) {
      setSourceCity(parts[0].charAt(0).toUpperCase() + parts[0].slice(1));
      setDestinationCity(parts[parts.length - 1].charAt(0).toUpperCase() + parts[parts.length - 1].slice(1));
    }
  }, [dataSource?.corridor, sourceTouched, destinationTouched]);

  useEffect(() => {
    if (!activeCorridorId) return;
    let isMounted = true;
    const rankingKey = `${operator}:${mode}:${blend}:${safetyMode}`;
    setLoadingRoutes(true);
    setError("");

    fetchRoutes({ operator, mode, eta_connectivity_blend: blend, safety_mode: safetyMode, corridor_id: activeCorridorId })
      .then((data) => {
        if (!isMounted) return;
        setRoutesResponse(data);
        const fallback = data.recommended_route_id;
        const rankingChanged = lastRankingKeyRef.current !== rankingKey;
        lastRankingKeyRef.current = rankingKey;
        setSelectedRouteId((current) => {
          const exists = data.routes.some((r) => r.route_id === current);
          if (!exists || rankingChanged) return fallback;
          return current;
        });
      })
      .catch((err) => { if (isMounted) setError(String(err)); })
      .finally(() => { if (isMounted) setLoadingRoutes(false); });

    return () => { isMounted = false; };
  }, [operator, mode, blend, safetyMode, activeCorridorId]);

  useEffect(() => {
    if (!playback || playback.steps.length === 0) return;
    setPlaybackIndex(0);
    const timer = window.setInterval(() => {
      setPlaybackIndex((current) => {
        if (current >= playback.steps.length - 1) { window.clearInterval(timer); return current; }
        return current + 1;
      });
    }, 300);
    return () => window.clearInterval(timer);
  }, [playback]);

  const routes = routesResponse?.routes ?? [];
  const corridorName = formatCorridorName(dataSource?.corridor);
  const operatorLabels = dataSource?.operator_labels ?? { jio: "Jio", airtel: "Airtel" };
  const operatorNote = dataSource?.operator_note ?? undefined;

  const selectedRoute = useMemo<Route | null>(() => {
    if (!routes.length) return null;
    return routes.find((r) => r.route_id === selectedRouteId) ?? routes[0];
  }, [routes, selectedRouteId]);

  const activeStep =
    playback && playbackIndex >= 0 && playbackIndex < playback.steps.length
      ? playback.steps[playbackIndex]
      : null;

  const mapActiveRouteId = activeStep?.route_id ?? selectedRouteId;
  const playbackSegmentIndex = activeStep?.segment_index ?? -1;

  async function runPlayback(decision: "continue" | "switch") {
    if (!selectedRoute) return;
    setLoadingPlayback(true);
    setError("");
    try {
      const response = await fetchPlayback({
        operator, route_id: selectedRoute.route_id, mode,
        eta_connectivity_blend: blend, safety_mode: safetyMode,
        decision_at_warning: decision, corridor_id: activeCorridorId ?? undefined,
      });
      setPlayback(response);
      setPlaybackIndex(-1);
      if (response.switched_route) setSelectedRouteId(response.final_route_id);
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
    <div className="flex h-[100dvh] w-screen flex-col overflow-hidden bg-[var(--surface)] text-[var(--text-primary)]">

      {/* ── Top Bar ─────────────────────────────────────── */}
      <header className="pointer-events-auto z-20 flex shrink-0 items-center gap-3 border-b border-[var(--border)] bg-[var(--card)] px-4 py-2.5 shadow-sm backdrop-blur-md">

        {/* Origin → Destination */}
        <div className="flex min-w-0 flex-1 items-center gap-2">
          <div className="flex min-w-0 flex-1 flex-col">
            <span className="text-[10px] font-semibold uppercase tracking-widest text-[var(--text-muted)]">Origin</span>
            <input
              value={sourceCity}
              onChange={(e) => { setSourceTouched(true); setSourceCity(e.target.value); }}
              className="w-full truncate bg-transparent text-lg font-extrabold leading-tight tracking-tight outline-none"
              placeholder="Source city"
            />
          </div>

          <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full border border-[var(--border)] bg-[var(--card-elevated)] text-sm font-bold text-[var(--text-muted)]">
            →
          </div>

          <div className="flex min-w-0 flex-1 flex-col">
            <span className="text-[10px] font-semibold uppercase tracking-widest text-[var(--text-muted)]">Destination</span>
            <input
              value={destinationCity}
              onChange={(e) => { setDestinationTouched(true); setDestinationCity(e.target.value); }}
              className="w-full truncate bg-transparent text-lg font-extrabold leading-tight tracking-tight outline-none"
              placeholder="Destination city"
            />
          </div>
        </div>

        {/* Corridor actions */}
        <div className="flex shrink-0 items-center gap-2">
          <button
            type="button"
            disabled={buildingCorridor}
            onClick={() => onBuildCorridor(false)}
            className="rounded-lg border border-[var(--border)] bg-[var(--card-elevated)] px-3 py-1.5 text-xs font-semibold shadow-sm transition hover:border-[var(--text-muted)] disabled:cursor-not-allowed disabled:opacity-60"
          >
            {buildingCorridor ? "Building…" : "Build Corridor"}
          </button>
          <button
            type="button"
            disabled={buildingCorridor}
            onClick={() => onBuildCorridor(true)}
            className="rounded-lg border border-[var(--border)] bg-[var(--card-elevated)] px-3 py-1.5 text-xs font-semibold shadow-sm transition hover:border-[var(--text-muted)] disabled:cursor-not-allowed disabled:opacity-60"
          >
            {buildingCorridor ? "Refreshing…" : "Refresh Data"}
          </button>
          {dataSource ? (
            <span className="hidden rounded-lg border border-[var(--border)] bg-[var(--card-elevated)] px-3 py-1.5 text-[11px] text-[var(--text-muted)] xl:inline-flex">
              {corridorName} · {dataSource.source_mode === "cached" ? "Cached OSRM+OpenCellID" : "Fallback Synthetic"}
            </span>
          ) : null}
        </div>

        {/* Theme toggle */}
        <div className="flex shrink-0 items-center gap-2">
          <span className="text-xs font-medium text-[var(--text-muted)]">{theme === "light" ? "Light" : "Dark"}</span>
          <button
            type="button"
            onClick={() => setTheme((t) => (t === "light" ? "dark" : "light"))}
            className={`theme-toggle ${theme === "dark" ? "is-dark" : ""}`}
            aria-label="Toggle theme"
            aria-pressed={theme === "dark"}
          >
            <span className="theme-toggle-knob" />
          </button>
        </div>

        {/* Analyze */}
        <button
          type="button"
          disabled={loadingRoutes || loadingPlayback || !selectedRoute}
          onClick={() => runPlayback(playbackDecision)}
          className="shrink-0 rounded-lg bg-black px-4 py-2 text-xs font-extrabold uppercase tracking-widest text-white shadow transition hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-60 dark:bg-white dark:text-black"
        >
          {loadingPlayback ? "…" : "Analyze"}
        </button>
      </header>

      {/* ── Status toasts ────────────────────────────────── */}
      {(job || error) ? (
        <div className="pointer-events-auto z-20 flex shrink-0 items-center gap-2 border-b border-[var(--border)] bg-[var(--card)] px-4 py-1.5">
          {job ? (
            <span className="text-[11px] text-[var(--text-muted)]">
              Job {job.job_id} · {job.stage} · {job.progress_pct}% · {job.status}
              {job.degraded && job.degraded_reason ? ` · ${job.degraded_reason}` : ""}
            </span>
          ) : null}
          {error ? (
            <span className="rounded-md border border-red-500/60 bg-red-500/10 px-2 py-0.5 text-[11px] text-red-600 dark:text-red-300">
              {error}
            </span>
          ) : null}
        </div>
      ) : null}

      {/* ── Main body: map + panels ──────────────────────── */}
      <div className="relative flex min-h-0 flex-1">

        {/* Full-bleed map layer */}
        <div className="absolute inset-0 z-0">
          <MapView
            routes={routes}
            selectedRouteId={mapActiveRouteId}
            playbackSegmentIndex={playbackSegmentIndex}
            startLabel={sourceLabel}
            endLabel={destinationLabel}
            theme={theme}
          />
        </div>

        {/* Left sidebar */}
        <div className="pointer-events-auto relative z-10 flex shrink-0 flex-col gap-3 overflow-y-auto p-3" style={{ width: 296 }}>
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
            onModeChange={handleModeChange}
            onBlendChange={setBlend}
            onSafetyModeChange={setSafetyMode}
            onPlaybackDecisionChange={setPlaybackDecision}
            onSelectRoute={setSelectedRouteId}
            theme={theme}
          />
        </div>

        {/* Right info column */}
        <div className="pointer-events-none relative z-10 ml-auto flex w-[320px] shrink-0 flex-col gap-3 p-3">

          {/* Route Insight card */}
          <div className="pointer-events-auto floating-card rounded-2xl p-4">
            <p className="mb-3 text-[10px] font-bold uppercase tracking-widest text-[var(--text-muted)]">Selected Route Insight</p>
            {selectedRoute ? (
              <div className="grid grid-cols-2 gap-3">
                {[
                  { label: "ETA", value: `${selectedRoute.eta_minutes} min` },
                  { label: "Distance", value: `${selectedRoute.distance_km} km` },
                  { label: "Connectivity", value: String(selectedRoute.connectivity_score) },
                  { label: "Longest Weak", value: `${selectedRoute.longest_weak_stretch_m} m` },
                ].map(({ label, value }) => (
                  <div key={label} className="rounded-xl border border-[var(--border)] bg-[var(--card-elevated)] px-3 py-2">
                    <p className="text-[10px] uppercase tracking-wide text-[var(--text-muted)]">{label}</p>
                    <p className="text-xl font-bold leading-tight">{value}</p>
                  </div>
                ))}
              </div>
            ) : activeCorridorId && !loadingRoutes ? (
              <div className="rounded-xl border border-red-500/40 bg-red-500/10 px-3 py-3 text-center">
                <p className="text-sm font-semibold text-red-600 dark:text-red-300">No route data found</p>
                <p className="mt-1 text-[11px] text-[var(--text-muted)]">
                  No connectivity data is available for this corridor. Try a different origin or destination.
                </p>
              </div>
            ) : activeCorridorId && loadingRoutes ? (
              <p className="text-xs text-[var(--text-muted)]">Loading route intelligence…</p>
            ) : (
              <p className="text-xs text-[var(--text-muted)]">Enter origin and destination, then click Build Corridor.</p>
            )}
          </div>

          {/* Timeline (always visible — shows prompt before playback, results after) */}
          {(routes.length > 0 || playback) ? (
            <div className="pointer-events-auto max-h-[min(38vh,340px)] overflow-auto rounded-2xl">
              <Timeline playback={playback} activeStep={activeStep} />
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}
