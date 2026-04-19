"use client";

import { useMemo } from "react";
import { NotificationEvent, PlaybackResponse, PlaybackStep } from "@/types/api";

interface TimelineProps {
  playback: PlaybackResponse | null;
  activeStep: PlaybackStep | null;
}

/* ── Visual helpers ──────────────────────────────────── */

function priorityBadge(priority: NotificationEvent["priority"]) {
  if (priority === "urgent") return "bg-red-500 text-white";
  if (priority === "semi-urgent") return "bg-amber-500 text-white";
  return "bg-[var(--card-elevated)] text-[var(--text-muted)]";
}

function priorityCard(priority: NotificationEvent["priority"], state: NotificationEvent["state"]) {
  if (state === "delivered") {
    if (priority === "urgent") return "border-red-500/50 bg-red-500/8";
    if (priority === "semi-urgent") return "border-amber-500/50 bg-amber-500/8";
    return "border-emerald-500/40 bg-emerald-500/8";
  }
  if (priority === "urgent") return "border-red-500/30 bg-red-500/5";
  if (priority === "semi-urgent") return "border-amber-500/30 bg-amber-500/5";
  return "border-[var(--border)] bg-[var(--card-elevated)]";
}

function stateLabel(event: NotificationEvent) {
  if (event.state === "delivered") return event.release_reason || "delivered";
  if (event.state === "deferred") return event.release_reason || "deferred — waiting for connectivity";
  if (event.state === "released") return "released — in transit";
  return "queued";
}

function zoneBadge(classification: string | undefined) {
  if (classification === "strong") return { text: "GREEN ZONE", cls: "bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border-emerald-500/30" };
  if (classification === "moderate") return { text: "YELLOW ZONE", cls: "bg-amber-500/15 text-amber-600 dark:text-amber-400 border-amber-500/30" };
  return { text: "RED ZONE", cls: "bg-red-500/15 text-red-600 dark:text-red-400 border-red-500/30" };
}

function formatRouteId(id: string) {
  return id.replace("osrm_route_", "Route ").replace("osrm_", "");
}

/* ── Component ───────────────────────────────────────── */

export function Timeline({ playback, activeStep }: TimelineProps) {
  if (!playback) {
    return (
      <section className="floating-card rounded-2xl p-5">
        <h2 className="text-sm font-bold uppercase tracking-widest text-[var(--text-muted)]">
          Notification Timeline
        </h2>
        <p className="mt-3 text-xs text-[var(--text-muted)]">
          Click <strong>Analyze</strong> to simulate connectivity-aware notification delivery along the selected route.
        </p>
      </section>
    );
  }

  /*
   * Zone-aware notification display:
   * - During playback (activeStep exists): show only visible_notifications from the current step
   * - After playback completes: show the final state (delivered + pending from the last step)
   */
  const isPlaying = activeStep !== null;
  const currentZone = activeStep?.classification;
  const zone = zoneBadge(currentZone);

  // Compute visible notifications for the current moment
  const { visibleDelivered, visiblePending, hiddenCount } = useMemo(() => {
    if (isPlaying && activeStep) {
      // During playback: use zone-filtered visible_notifications from the active step
      const visible = activeStep.visible_notifications ?? [];
      const delivered = visible.filter((n) => n.state === "delivered");
      const pending = visible.filter((n) => n.state !== "delivered");
      const totalQueue = playback.delivered_notifications.length + playback.pending_notifications.length;
      const hidden = totalQueue - visible.length;
      return { visibleDelivered: delivered, visiblePending: pending, hiddenCount: Math.max(0, hidden) };
    }

    // After playback: show final state from the last step
    const lastStep = playback.steps[playback.steps.length - 1];
    if (lastStep?.visible_notifications) {
      const visible = lastStep.visible_notifications;
      const delivered = visible.filter((n) => n.state === "delivered");
      const pending = visible.filter((n) => n.state !== "delivered");
      return { visibleDelivered: delivered, visiblePending: pending, hiddenCount: 0 };
    }

    // Fallback: legacy behavior
    return {
      visibleDelivered: playback.delivered_notifications,
      visiblePending: playback.pending_notifications,
      hiddenCount: 0,
    };
  }, [activeStep, isPlaying, playback]);

  return (
    <section className="floating-card rounded-2xl p-4">
      {/* Header */}
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-[10px] font-bold uppercase tracking-widest text-[var(--text-muted)]">
          Notification Timeline
        </h2>
        <span className="rounded-full border border-[var(--border)] bg-[var(--card-elevated)] px-2 py-0.5 text-[9px] uppercase tracking-wider text-[var(--text-muted)]">
          {playback.switched_route ? "Route Switched" : "Same Route"}
        </span>
      </div>

      {/* Current zone indicator during playback */}
      {isPlaying ? (
        <div className={`mb-3 flex items-center justify-between rounded-xl border px-3 py-2 ${zone.cls}`}>
          <div className="flex items-center gap-2">
            <span className="relative flex h-2 w-2">
              <span className={`absolute inline-flex h-full w-full animate-ping rounded-full opacity-75 ${
                currentZone === "strong" ? "bg-emerald-500" : currentZone === "moderate" ? "bg-amber-500" : "bg-red-500"
              }`} />
              <span className={`relative inline-flex h-2 w-2 rounded-full ${
                currentZone === "strong" ? "bg-emerald-500" : currentZone === "moderate" ? "bg-amber-500" : "bg-red-500"
              }`} />
            </span>
            <span className="text-[10px] font-bold uppercase tracking-wider">{zone.text}</span>
          </div>
          <span className="text-[9px] font-medium opacity-70">
            Segment {activeStep?.segment_index ?? 0}
          </span>
        </div>
      ) : null}

      {/* Zone policy reminder during playback */}
      {isPlaying && currentZone ? (
        <div className="mb-3 rounded-lg border border-[var(--border)] bg-[var(--card-elevated)] px-3 py-1.5">
          <p className="text-[9px] font-semibold uppercase tracking-wider text-[var(--text-muted)]">
            {currentZone === "strong"
              ? "All notifications visible · releasing in controlled order"
              : currentZone === "moderate"
                ? "Urgent & semi-urgent visible · non-urgent hidden"
                : "Only urgent notifications visible"}
          </p>
        </div>
      ) : null}

      {/* Weak-zone warning */}
      {activeStep?.warning ? (
        <div className="animate-pulse-soft mb-3 rounded-xl border border-red-500/60 bg-red-500/10 px-3 py-2">
          <p className="text-xs font-semibold text-red-600 dark:text-red-300">⚠ Weak-zone warning ahead</p>
          <p className="mt-0.5 text-[10px] text-[var(--text-muted)]">
            Weak segment in {activeStep.warning.distance_to_weak_zone_m} m · ~{activeStep.warning.estimated_weak_zone_length_m} m long
          </p>
        </div>
      ) : null}

      {/* Stats grid — 2×2 */}
      <div className="mb-3 grid grid-cols-2 gap-2">
        <div className="rounded-xl border border-[var(--border)] bg-[var(--card-elevated)] px-3 py-2 text-center">
          <p className="text-[9px] uppercase tracking-wider text-[var(--text-muted)]">Initial Route</p>
          <p className="mt-0.5 truncate text-sm font-bold" title={playback.initial_route_id}>
            {formatRouteId(playback.initial_route_id)}
          </p>
        </div>
        <div className="rounded-xl border border-[var(--border)] bg-[var(--card-elevated)] px-3 py-2 text-center">
          <p className="text-[9px] uppercase tracking-wider text-[var(--text-muted)]">Final Route</p>
          <p className="mt-0.5 truncate text-sm font-bold" title={playback.final_route_id}>
            {formatRouteId(playback.final_route_id)}
          </p>
        </div>
        <div className="rounded-xl border border-emerald-500/40 bg-emerald-500/8 px-3 py-2 text-center">
          <p className="text-[9px] uppercase tracking-wider text-[var(--text-muted)]">Delivered</p>
          <p className="mt-0.5 text-lg font-extrabold text-emerald-600 dark:text-emerald-400">
            {visibleDelivered.length}
          </p>
        </div>
        <div className="rounded-xl border border-[var(--border)] bg-[var(--card-elevated)] px-3 py-2 text-center">
          <p className="text-[9px] uppercase tracking-wider text-[var(--text-muted)]">
            {hiddenCount > 0 ? "Pending / Hidden" : "Pending"}
          </p>
          <p className="mt-0.5 text-lg font-extrabold">
            {visiblePending.length}
            {hiddenCount > 0 ? (
              <span className="ml-1 text-xs font-medium text-[var(--text-muted)]">+{hiddenCount}</span>
            ) : null}
          </p>
        </div>
      </div>

      {/* Notification cards */}
      <div className="flex max-h-[320px] flex-col gap-2 overflow-y-auto pr-1">
        {/* Delivered notifications */}
        {visibleDelivered.map((event) => (
          <article
            key={event.id}
            className={`rounded-xl border p-3 transition-all duration-300 ${priorityCard(event.priority, event.state)}`}
          >
            <div className="flex items-start justify-between gap-2">
              <h3 className="text-xs font-semibold leading-tight text-[var(--text-primary)]">{event.title}</h3>
              <span className={`shrink-0 rounded-full px-1.5 py-0.5 text-[8px] font-bold uppercase tracking-wider ${priorityBadge(event.priority)}`}>
                {event.priority}
              </span>
            </div>
            <p className="mt-1 text-[11px] text-[var(--text-muted)]">{stateLabel(event)}</p>
            <p className="mt-0.5 text-[9px] font-medium uppercase tracking-wider text-[var(--text-muted)]">
              Delivered at segment {event.released_at_segment ?? "—"}
            </p>
          </article>
        ))}

        {/* Visible pending notifications */}
        {visiblePending.length > 0 ? (
          <>
            <p className="mt-1 text-[9px] font-bold uppercase tracking-widest text-[var(--text-muted)]">
              Waiting
            </p>
            {visiblePending.map((event) => (
              <article
                key={event.id}
                className={`rounded-xl border border-dashed p-3 opacity-70 transition-all duration-300 ${priorityCard(event.priority, event.state)}`}
              >
                <div className="flex items-start justify-between gap-2">
                  <h3 className="text-xs font-semibold text-[var(--text-primary)]">{event.title}</h3>
                  <span className={`shrink-0 rounded-full px-1.5 py-0.5 text-[8px] font-bold uppercase tracking-wider ${priorityBadge(event.priority)}`}>
                    {event.priority}
                  </span>
                </div>
                <p className="mt-1 text-[10px] text-[var(--text-muted)]">{stateLabel(event)}</p>
              </article>
            ))}
          </>
        ) : null}

        {/* Hidden count indicator */}
        {hiddenCount > 0 ? (
          <div className="mt-1 flex items-center gap-2 rounded-lg border border-dashed border-[var(--border)] bg-[var(--card-elevated)] px-3 py-2 opacity-50">
            <svg className="h-3.5 w-3.5 shrink-0 text-[var(--text-muted)]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M3 3l18 18" />
            </svg>
            <p className="text-[10px] font-medium text-[var(--text-muted)]">
              {hiddenCount} notification{hiddenCount === 1 ? "" : "s"} hidden in current zone
            </p>
          </div>
        ) : null}
      </div>
    </section>
  );
}
