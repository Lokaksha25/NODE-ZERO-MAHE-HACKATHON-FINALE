"use client";

import { RankingMode, Route } from "@/types/api";

interface ControlPanelProps {
  operator: "jio" | "airtel";
  operatorLabels: Record<"jio" | "airtel", string>;
  operatorNote?: string;
  mode: RankingMode;
  blend: number;
  safetyMode: boolean;
  routes: Route[];
  selectedRouteId: string;
  loading: boolean;
  onOperatorChange: (operator: "jio" | "airtel") => void;
  onModeChange: (mode: RankingMode) => void;
  onBlendChange: (value: number) => void;
  onSafetyModeChange: (value: boolean) => void;
  onSelectRoute: (routeId: string) => void;
  onRunPlayback: (decision: "continue" | "switch") => void;
}

export function ControlPanel({
  operator,
  operatorLabels,
  operatorNote,
  mode,
  blend,
  safetyMode,
  routes,
  selectedRouteId,
  loading,
  onOperatorChange,
  onModeChange,
  onBlendChange,
  onSafetyModeChange,
  onSelectRoute,
  onRunPlayback,
}: ControlPanelProps) {
  return (
    <aside className="animate-rise rounded-2xl border border-dusk-400/30 bg-dusk-800/75 p-5 backdrop-blur-lg">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-lg font-semibold">Demo Controls</h2>
        {safetyMode ? (
          <span className="rounded-full border border-coral/60 bg-coral/15 px-2 py-1 text-xs font-semibold uppercase tracking-wider text-coral">
            Safety Mode Active
          </span>
        ) : null}
      </div>

      <div className="flex flex-col gap-4">
        <div>
          <p className="mb-2 text-xs uppercase tracking-wide text-dusk-200">Operator</p>
          {operatorNote ? <p className="mb-2 text-xs text-dusk-200">{operatorNote}</p> : null}
          <div className="grid grid-cols-2 gap-2">
            <button
              type="button"
              className={`rounded-xl border px-3 py-2 text-sm font-medium transition ${
                operator === "jio"
                  ? "border-ember bg-ember/20 text-ember"
                  : "border-dusk-400/45 bg-dusk-700/50 text-dusk-100 hover:border-dusk-200"
              }`}
              onClick={() => onOperatorChange("jio")}
            >
              {operatorLabels.jio}
            </button>
            <button
              type="button"
              className={`rounded-xl border px-3 py-2 text-sm font-medium transition ${
                operator === "airtel"
                  ? "border-ember bg-ember/20 text-ember"
                  : "border-dusk-400/45 bg-dusk-700/50 text-dusk-100 hover:border-dusk-200"
              }`}
              onClick={() => onOperatorChange("airtel")}
            >
              {operatorLabels.airtel}
            </button>
          </div>
        </div>

        <div>
          <p className="mb-2 text-xs uppercase tracking-wide text-dusk-200">Ranking Mode</p>
          <div className="grid grid-cols-2 gap-2">
            <button
              type="button"
              className={`rounded-xl border px-3 py-2 text-sm font-medium transition ${
                mode === "fastest"
                  ? "border-moss bg-moss/20 text-moss"
                  : "border-dusk-400/45 bg-dusk-700/50 text-dusk-100 hover:border-dusk-200"
              }`}
              onClick={() => onModeChange("fastest")}
            >
              Fastest
            </button>
            <button
              type="button"
              className={`rounded-xl border px-3 py-2 text-sm font-medium transition ${
                mode === "most_connected"
                  ? "border-moss bg-moss/20 text-moss"
                  : "border-dusk-400/45 bg-dusk-700/50 text-dusk-100 hover:border-dusk-200"
              }`}
              onClick={() => onModeChange("most_connected")}
            >
              Most Connected
            </button>
          </div>
        </div>

        <div>
          <label htmlFor="blend" className="mb-2 block text-xs uppercase tracking-wide text-dusk-200">
            ETA vs Connectivity Blend ({Math.round(blend * 100)}%)
          </label>
          <input
            id="blend"
            type="range"
            min={0}
            max={1}
            step={0.05}
            value={blend}
            onChange={(event) => onBlendChange(Number(event.target.value))}
            className="w-full accent-ember"
          />
        </div>

        <label className="flex cursor-pointer items-center gap-2 rounded-xl border border-dusk-400/45 bg-dusk-700/50 px-3 py-2 text-sm">
          <input
            type="checkbox"
            checked={safetyMode}
            onChange={(event) => onSafetyModeChange(event.target.checked)}
            className="accent-coral"
          />
          Enable safety-prioritized mode
        </label>
      </div>

      <div className="mt-6 flex flex-col gap-2">
        <p className="text-xs uppercase tracking-wide text-dusk-200">Route Alternatives</p>
        {routes.map((route) => (
          <button
            type="button"
            key={route.route_id}
            onClick={() => onSelectRoute(route.route_id)}
            className={`rounded-xl border p-3 text-left transition ${
              route.route_id === selectedRouteId
                ? "border-ember bg-ember/15"
                : "border-dusk-400/45 bg-dusk-700/40 hover:border-dusk-200"
            }`}
          >
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold">{route.label}</h3>
              {route.is_recommended ? (
                <span className="rounded-full bg-moss/20 px-2 py-1 text-[10px] font-semibold uppercase tracking-widest text-moss">
                  Recommended
                </span>
              ) : null}
            </div>
            <p className="mt-1 text-xs text-dusk-100">
              ETA {route.eta_minutes} min | {route.distance_km} km | Connectivity {route.connectivity_score}
            </p>
            <p className="text-xs text-dusk-200">
              Longest weak stretch: {route.longest_weak_stretch_m} m
            </p>
          </button>
        ))}
      </div>

      <div className="mt-6 grid grid-cols-2 gap-2">
        <button
          type="button"
          disabled={loading}
          onClick={() => onRunPlayback("continue")}
          className="rounded-xl border border-amber bg-amber/20 px-3 py-2 text-sm font-semibold text-amber transition hover:bg-amber/30 disabled:cursor-not-allowed disabled:opacity-70"
        >
          Play: Continue
        </button>
        <button
          type="button"
          disabled={loading}
          onClick={() => onRunPlayback("switch")}
          className="rounded-xl border border-moss bg-moss/20 px-3 py-2 text-sm font-semibold text-moss transition hover:bg-moss/30 disabled:cursor-not-allowed disabled:opacity-70"
        >
          Play: Switch Route
        </button>
      </div>
    </aside>
  );
}
