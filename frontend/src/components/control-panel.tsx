"use client";

import { RankingMode, Route } from "@/types/api";

interface ControlPanelProps {
  operator: "all" | "jio" | "airtel";
  operatorLabels: Record<"jio" | "airtel", string>;
  operatorNote?: string;
  mode: RankingMode;
  blend: number;
  safetyMode: boolean;
  playbackDecision: "continue" | "switch";
  routes: Route[];
  selectedRouteId: string;
  loading: boolean;
  onOperatorChange: (operator: "all" | "jio" | "airtel") => void;
  onModeChange: (mode: RankingMode) => void;
  onBlendChange: (value: number) => void;
  onSafetyModeChange: (value: boolean) => void;
  onPlaybackDecisionChange: (value: "continue" | "switch") => void;
  onSelectRoute: (routeId: string) => void;
  theme: "light" | "dark";
}

export function ControlPanel({
  operator,
  operatorLabels,
  operatorNote,
  mode,
  blend,
  safetyMode,
  playbackDecision,
  routes,
  selectedRouteId,
  loading,
  onOperatorChange,
  onModeChange,
  onBlendChange,
  onSafetyModeChange,
  onPlaybackDecisionChange,
  onSelectRoute,
  theme,
}: ControlPanelProps) {
  const isLight = theme === "light";
  const baseBtn = isLight
    ? "border-slate-300 bg-white text-slate-900 hover:border-slate-500"
    : "border-slate-600 bg-slate-900 text-slate-100 hover:border-slate-400";

  return (
    <aside
      className="floating-card animate-rise w-[300px] max-h-[calc(100vh-280px)] overflow-y-auto rounded-2xl p-4 md:p-5"
      onWheelCapture={(event) => event.stopPropagation()}
    >
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-[42px] font-extrabold leading-none tracking-tight">Demo Controls</h2>
        {safetyMode ? (
          <span className="rounded-full border border-red-500/70 bg-red-500/10 px-2 py-1 text-[10px] font-semibold uppercase tracking-wider text-red-500">
            Safety
          </span>
        ) : null}
      </div>

      <div className="flex flex-col gap-4">
        <div>
          <p className="mb-2 text-[33px] font-semibold leading-none">Operator</p>
          {operatorNote ? <p className="mb-2 text-xs opacity-75">{operatorNote}</p> : null}
          <div className="grid grid-cols-3 gap-2">
            <button
              type="button"
              className={`whitespace-nowrap rounded-xl border px-2 py-2 text-[10px] font-semibold transition ${
                operator === "all"
                  ? "border-black bg-black text-white dark:border-white dark:bg-white dark:text-black"
                  : baseBtn
              }`}
              onClick={() => onOperatorChange("all")}
            >
              All Networks
            </button>
            <button
              type="button"
              className={`whitespace-nowrap rounded-xl border px-2 py-2 text-[10px] font-semibold transition ${
                operator === "jio"
                  ? "border-black bg-black text-white dark:border-white dark:bg-white dark:text-black"
                  : baseBtn
              }`}
              onClick={() => onOperatorChange("jio")}
            >
              {operatorLabels.jio}
            </button>
            <button
              type="button"
              className={`whitespace-nowrap rounded-xl border px-2 py-2 text-[10px] font-semibold transition ${
                operator === "airtel"
                  ? "border-black bg-black text-white dark:border-white dark:bg-white dark:text-black"
                  : baseBtn
              }`}
              onClick={() => onOperatorChange("airtel")}
            >
              {operatorLabels.airtel}
            </button>
          </div>
        </div>

        <div>
          <p className="mb-2 text-[33px] font-semibold leading-none">Ranking Mode</p>
          <div className="grid grid-cols-2 gap-2">
            <button
              type="button"
              className={`rounded-xl border px-3 py-2 text-sm font-semibold transition ${
                mode === "fastest"
                  ? "border-black bg-black text-white dark:border-white dark:bg-white dark:text-black"
                  : baseBtn
              }`}
              onClick={() => onModeChange("fastest")}
            >
              Fastest
            </button>
            <button
              type="button"
              className={`rounded-xl border px-3 py-2 text-sm font-semibold transition ${
                mode === "most_connected"
                  ? "border-black bg-black text-white dark:border-white dark:bg-white dark:text-black"
                  : baseBtn
              }`}
              onClick={() => onModeChange("most_connected")}
            >
              Most Connected
            </button>
          </div>
        </div>

        <div>
          <label htmlFor="blend" className="mb-2 block text-[33px] font-semibold leading-none">
            ETA vs Connectivity
          </label>
          <input
            id="blend"
            type="range"
            min={0}
            max={1}
            step={0.05}
            value={blend}
            onChange={(event) => onBlendChange(Number(event.target.value))}
            className="corridor-slider w-full"
          />
          <p className="mt-1 text-xs opacity-70">Bias: {Math.round(blend * 100)}% ETA / {100 - Math.round(blend * 100)}% connectivity</p>
        </div>

        <label className="flex cursor-pointer items-center gap-2 rounded-xl border border-[var(--border)] bg-[var(--card-elevated)] px-3 py-2 text-sm">
          <input
            type="checkbox"
            checked={safetyMode}
            onChange={(event) => onSafetyModeChange(event.target.checked)}
            className="accent-red-500"
          />
          Safety-prioritized mode
        </label>

        <label className="flex cursor-pointer items-center gap-2 rounded-xl border border-[var(--border)] bg-[var(--card-elevated)] px-3 py-2 text-sm">
          <input
            type="checkbox"
            checked={playbackDecision === "switch"}
            onChange={(event) => onPlaybackDecisionChange(event.target.checked ? "switch" : "continue")}
            className="accent-black dark:accent-white"
          />
          Auto-switch on weak warning
        </label>
      </div>

      <div className="mt-6 flex flex-col gap-2">
        <p className="text-xs font-semibold uppercase tracking-wide opacity-65">Route Alternatives</p>
        {routes.map((route) => (
          <button
            type="button"
            key={route.route_id}
            onClick={() => onSelectRoute(route.route_id)}
            className={`rounded-xl border p-3 text-left transition ${
              route.route_id === selectedRouteId
                ? "border-black bg-black text-white dark:border-white dark:bg-white dark:text-black"
                : "border-[var(--border)] bg-[var(--card-elevated)] hover:border-[var(--text-muted)]"
            }`}
          >
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold leading-tight">{route.label}</h3>
              {route.is_recommended ? (
                <span className="rounded-full bg-emerald-500/20 px-2 py-1 text-[10px] font-semibold uppercase tracking-widest text-emerald-600 dark:text-emerald-300">
                  Recommended
                </span>
              ) : null}
            </div>
            <p className="mt-1 text-xs opacity-85">
              ETA {route.eta_minutes} min | {route.distance_km} km | Connectivity {route.connectivity_score}
            </p>
            <p className="text-xs opacity-65">
              Longest weak stretch: {route.longest_weak_stretch_m} m
            </p>
          </button>
        ))}
      </div>
      {loading ? <p className="mt-4 text-xs opacity-65">Running analysis...</p> : null}
    </aside>
  );
}
