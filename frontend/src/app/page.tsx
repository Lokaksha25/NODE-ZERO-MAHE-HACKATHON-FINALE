"use client";

import dynamic from "next/dynamic";
import { useEffect, useMemo, useRef, useState } from "react";

import { ControlPanel } from "@/components/control-panel";
import { Timeline } from "@/components/timeline";
import { fetchDataSourceStatus, fetchPlayback, fetchRoutes } from "@/lib/api";
import {
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

export default function Home() {
  const [operator, setOperator] = useState<Operator>("jio");
  const [mode, setMode] = useState<RankingMode>("fastest");
  const [blend, setBlend] = useState<number>(0.5);
  const [safetyMode, setSafetyMode] = useState<boolean>(false);

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
    let isMounted = true;

    fetchDataSourceStatus()
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
  }, []);

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
  }, [operator, mode, blend, safetyMode]);

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
  const usesNorwayAliases = dataSource?.corridor === "oslo-drammen";
  const operatorLabels = usesNorwayAliases
    ? { jio: "Telenor-like", airtel: "Telia-like" }
    : { jio: "Jio", airtel: "Airtel" };
  const operatorNote = usesNorwayAliases
    ? "This Oslo cache remaps local Norway operator groups into the legacy jio/airtel demo slots."
    : undefined;

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

  return (
    <main className="min-h-screen bg-mesh-atmos p-4 text-dusk-50 sm:p-6">
      <div className="mx-auto flex max-w-[1400px] flex-col gap-4">
        <header className="animate-rise rounded-2xl border border-dusk-300/35 bg-dusk-800/70 p-5 backdrop-blur-lg">
          <h1 className="text-2xl font-bold sm:text-3xl">Node Zero Corridor Intelligence</h1>
          <p className="mt-2 max-w-4xl text-sm text-dusk-100">
            Carrier-specific coverage estimation for {corridorName} with deterministic route scoring,
            weak-zone warnings, and geo-deferred notification playback.
          </p>
          <div className="mt-3 flex flex-wrap gap-2 text-xs">
            <span className="rounded-full border border-moss/60 bg-moss/15 px-2 py-1">Strong coverage</span>
            <span className="rounded-full border border-amber/60 bg-amber/15 px-2 py-1">Moderate coverage</span>
            <span className="rounded-full border border-coral/60 bg-coral/15 px-2 py-1">Weak coverage</span>
            {dataSource ? (
              <span
                className={`rounded-full border px-2 py-1 ${
                  dataSource.source_mode === "cached"
                    ? "border-moss/60 bg-moss/15 text-moss"
                    : "border-amber/60 bg-amber/15 text-amber"
                }`}
              >
                Data: {dataSource.source_mode === "cached" ? "Cached OSRM+OpenCellID" : "Fallback Synthetic"}
              </span>
            ) : null}
          </div>
        </header>

        {dataSource ? (
          <section className="rounded-xl border border-dusk-400/45 bg-dusk-800/55 p-3 text-xs text-dusk-100">
            Source: {dataSource.source_name} | Corridor: {corridorName} | Routes: {dataSource.route_count} | Towers: {dataSource.tower_count}
            {dataSource.generated_at > 0
              ? ` | Generated: ${new Date(dataSource.generated_at * 1000).toLocaleString()}`
              : " | Generated: n/a"}
          </section>
        ) : null}

        {error ? (
          <section className="rounded-xl border border-coral/60 bg-coral/10 p-3 text-sm text-coral">
            {error}
          </section>
        ) : null}

        <section className="grid grid-cols-1 gap-4 xl:grid-cols-[340px_minmax(0,1fr)]">
          <ControlPanel
            operator={operator}
            operatorLabels={operatorLabels}
            operatorNote={operatorNote}
            mode={mode}
            blend={blend}
            safetyMode={safetyMode}
            routes={routes}
            selectedRouteId={selectedRouteId}
            loading={loadingRoutes || loadingPlayback}
            onOperatorChange={setOperator}
            onModeChange={setMode}
            onBlendChange={setBlend}
            onSafetyModeChange={setSafetyMode}
            onSelectRoute={setSelectedRouteId}
            onRunPlayback={runPlayback}
          />

          <div className="flex flex-col gap-4">
            <MapView
              routes={routes}
              selectedRouteId={mapActiveRouteId}
              playbackSegmentIndex={playbackSegmentIndex}
            />

            <section className="rounded-2xl border border-dusk-400/30 bg-dusk-800/75 p-5 backdrop-blur-lg">
              <h2 className="text-lg font-semibold">Selected Route Insight</h2>
              {selectedRoute ? (
                <div className="mt-3 grid grid-cols-2 gap-3 text-sm sm:grid-cols-4">
                  <div className="rounded-xl border border-dusk-400/35 bg-dusk-700/35 p-3">
                    <p className="text-xs uppercase tracking-wide text-dusk-200">ETA</p>
                    <p className="font-semibold text-dusk-50">{selectedRoute.eta_minutes} min</p>
                  </div>
                  <div className="rounded-xl border border-dusk-400/35 bg-dusk-700/35 p-3">
                    <p className="text-xs uppercase tracking-wide text-dusk-200">Distance</p>
                    <p className="font-semibold text-dusk-50">{selectedRoute.distance_km} km</p>
                  </div>
                  <div className="rounded-xl border border-dusk-400/35 bg-dusk-700/35 p-3">
                    <p className="text-xs uppercase tracking-wide text-dusk-200">Connectivity</p>
                    <p className="font-semibold text-dusk-50">{selectedRoute.connectivity_score}</p>
                  </div>
                  <div className="rounded-xl border border-dusk-400/35 bg-dusk-700/35 p-3">
                    <p className="text-xs uppercase tracking-wide text-dusk-200">Longest Weak Stretch</p>
                    <p className="font-semibold text-dusk-50">{selectedRoute.longest_weak_stretch_m} m</p>
                  </div>
                </div>
              ) : (
                <p className="mt-3 text-sm text-dusk-100">Loading route intelligence...</p>
              )}
            </section>

            <Timeline playback={playback} activeStep={activeStep} />
          </div>
        </section>
      </div>
    </main>
  );
}
