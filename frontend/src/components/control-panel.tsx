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
    ? "border-slate-200 bg-white text-slate-700 hover:border-slate-400"
    : "border-slate-600 bg-slate-800 text-slate-200 hover:border-slate-400";

  return (
    <aside
      className="floating-card animate-rise flex flex-col gap-4 overflow-y-auto rounded-2xl p-4 hide-scrollbar"
      style={{ maxHeight: "calc(100vh - 200px)" }}
      onWheelCapture={(event) => event.stopPropagation()}
    >
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-bold tracking-tight">Demo Controls</h2>
        {safetyMode ? (
          <span className="rounded-full border border-red-500/60 bg-red-500/10 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-red-500">
            Safety On
          </span>
        ) : null}
      </div>

      <div className="h-px bg-[var(--border)]" />

      {/* Operator */}
      <div className="flex flex-col gap-2">
        <p className="text-[10px] font-bold uppercase tracking-widest text-[var(--text-muted)]">Operator</p>
        {operatorNote ? (
          <p className="text-[11px] leading-snug text-[var(--text-muted)]">{operatorNote}</p>
        ) : null}
        <div className="grid grid-cols-3 gap-1">
          {(["all", "jio", "airtel"] as const).map((op) => (
            <button
              key={op}
              type="button"
              className={`overflow-hidden truncate rounded-lg border px-1.5 py-2 text-center text-[10px] font-semibold leading-none transition ${
                operator === op
                  ? "border-black bg-black text-white dark:border-white dark:bg-white dark:text-black"
                  : baseBtn
              }`}
              onClick={() => onOperatorChange(op)}
              title={op === "all" ? "All Networks" : op === "jio" ? operatorLabels.jio : operatorLabels.airtel}
            >
              {op === "all" ? "All Networks" : op === "jio" ? operatorLabels.jio : operatorLabels.airtel}
            </button>
          ))}
        </div>
      </div>

      <div className="h-px bg-[var(--border)]" />

      {/* Ranking Mode */}
      <div className="flex flex-col gap-2">
        <p className="text-[10px] font-bold uppercase tracking-widest text-[var(--text-muted)]">Ranking Mode</p>
        <div className="grid grid-cols-2 gap-1.5">
          {(["fastest", "most_connected"] as const).map((m) => (
            <button
              key={m}
              type="button"
              className={`rounded-lg border px-2 py-1.5 text-xs font-semibold transition ${
                mode === m
                  ? "border-black bg-black text-white dark:border-white dark:bg-white dark:text-black"
                  : baseBtn
              }`}
              onClick={() => onModeChange(m)}
            >
              {m === "fastest" ? "Fastest" : "Most Connected"}
            </button>
          ))}
        </div>
      </div>

      <div className="h-px bg-[var(--border)]" />

      {/* Blend Slider */}
      <div className="flex flex-col gap-2">
        <div className="flex items-center justify-between">
          <p className="text-[10px] font-bold uppercase tracking-widest text-[var(--text-muted)]">ETA vs Connectivity</p>
          <span className="text-[11px] font-semibold">
            {Math.round(blend * 100)}% / {100 - Math.round(blend * 100)}%
          </span>
        </div>
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
        <div className="flex justify-between text-[10px] text-[var(--text-muted)]">
          <span>Speed</span>
          <span>Coverage</span>
        </div>
      </div>

      <div className="h-px bg-[var(--border)]" />

      {/* Toggles */}
      <div className="flex flex-col gap-2">
        <p className="text-[10px] font-bold uppercase tracking-widest text-[var(--text-muted)]">Options</p>
        <label className="flex cursor-pointer items-center gap-2.5 rounded-lg border border-[var(--border)] bg-[var(--card-elevated)] px-3 py-2 text-xs font-medium">
          <input
            type="checkbox"
            checked={safetyMode}
            onChange={(event) => onSafetyModeChange(event.target.checked)}
            className="accent-red-500"
          />
          Safety-prioritized mode
        </label>
      </div>

      <div className="h-px bg-[var(--border)]" />

      {/* Route Alternatives */}
      <div className="flex flex-col gap-2">
        <p className="text-[10px] font-bold uppercase tracking-widest text-[var(--text-muted)]">Route Alternatives</p>
        {routes.length === 0 && !loading ? (
          <p className="text-xs text-[var(--text-muted)]">No routes loaded.</p>
        ) : null}
        {routes.map((route) => (
          <button
            type="button"
            key={route.route_id}
            onClick={() => onSelectRoute(route.route_id)}
            className={`rounded-xl border p-2.5 text-left transition ${
              route.route_id === selectedRouteId
                ? "border-black bg-black text-white dark:border-white dark:bg-white dark:text-black"
                : "border-[var(--border)] bg-[var(--card-elevated)] hover:border-[var(--text-muted)]"
            }`}
          >
            <div className="flex items-start justify-between gap-1">
              <span className="text-xs font-semibold leading-tight">{route.label}</span>
              {route.is_recommended ? (
                <span className="shrink-0 rounded-full bg-emerald-500/20 px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-widest text-emerald-600 dark:text-emerald-300">
                  Best
                </span>
              ) : null}
            </div>
            <p className="mt-1 text-[11px] opacity-75">
              {route.eta_minutes} min · {route.distance_km} km · Score {route.connectivity_score}
            </p>
            <p className="text-[10px] opacity-50">Longest weak: {route.longest_weak_stretch_m} m</p>
          </button>
        ))}
        {loading ? (
          <p className="text-center text-[11px] text-[var(--text-muted)]">Analyzing…</p>
        ) : null}
      </div>
    </aside>
  );
}
