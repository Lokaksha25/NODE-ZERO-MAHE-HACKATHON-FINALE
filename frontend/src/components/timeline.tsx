"use client";

import { NotificationEvent, PlaybackResponse, PlaybackStep } from "@/types/api";

interface TimelineProps {
  playback: PlaybackResponse | null;
  activeStep: PlaybackStep | null;
}

function priorityClass(priority: NotificationEvent["priority"]) {
  if (priority === "urgent") {
    return "border-red-500/70 bg-red-500/10 text-red-600 dark:text-red-300";
  }
  if (priority === "semi-urgent") {
    return "border-amber-500/70 bg-amber-500/10 text-amber-700 dark:text-amber-300";
  }
  return "border-[var(--border)] bg-[var(--card-elevated)] text-[var(--text-primary)]";
}

export function Timeline({ playback, activeStep }: TimelineProps) {
  if (!playback) {
    return (
      <section className="floating-card rounded-2xl p-5">
        <h2 className="text-lg font-semibold">Notification Timeline</h2>
        <p className="mt-3 text-sm text-[var(--text-muted)]">
          Start playback to visualize deferred and delivered notifications along connectivity segments.
        </p>
      </section>
    );
  }

  return (
    <section className="floating-card rounded-2xl p-5">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-lg font-semibold">Notification Timeline</h2>
        <p className="text-xs uppercase tracking-wider text-[var(--text-muted)]">
          {playback.switched_route ? "Switched to better-connected route" : "Stayed on selected route"}
        </p>
      </div>

      {activeStep?.warning ? (
        <div className="animate-pulse-soft mb-4 rounded-xl border border-red-500/60 bg-red-500/10 p-3">
          <p className="text-sm font-semibold text-red-600 dark:text-red-300">Weak-zone warning ahead</p>
          <p className="text-xs text-[var(--text-muted)]">
            Weak segment in {activeStep.warning.distance_to_weak_zone_m} m, estimated length {activeStep.warning.estimated_weak_zone_length_m} m.
            Better-connected option: {activeStep.warning.better_connected_route_id}
          </p>
        </div>
      ) : null}

      <div className="mb-4 grid grid-cols-2 gap-3 text-xs text-[var(--text-primary)] sm:grid-cols-4">
        <div className="rounded-xl border border-[var(--border)] bg-[var(--card-elevated)] p-2">
          <p className="text-[var(--text-muted)]">Initial Route</p>
          <p className="font-semibold">{playback.initial_route_id}</p>
        </div>
        <div className="rounded-xl border border-[var(--border)] bg-[var(--card-elevated)] p-2">
          <p className="text-[var(--text-muted)]">Final Route</p>
          <p className="font-semibold">{playback.final_route_id}</p>
        </div>
        <div className="rounded-xl border border-[var(--border)] bg-[var(--card-elevated)] p-2">
          <p className="text-[var(--text-muted)]">Delivered</p>
          <p className="font-semibold">{playback.delivered_notifications.length}</p>
        </div>
        <div className="rounded-xl border border-[var(--border)] bg-[var(--card-elevated)] p-2">
          <p className="text-[var(--text-muted)]">Pending</p>
          <p className="font-semibold">{playback.pending_notifications.length}</p>
        </div>
      </div>

      <div className="flex max-h-[360px] flex-col gap-2 overflow-y-auto pr-1">
        {playback.delivered_notifications.map((event) => (
          <article key={event.id} className={`rounded-xl border p-3 text-sm ${priorityClass(event.priority)}`}>
            <div className="mb-1 flex items-center justify-between">
              <h3 className="font-semibold">{event.title}</h3>
              <span className="text-[10px] uppercase tracking-widest">{event.priority}</span>
            </div>
            <p className="text-xs">{event.release_reason}</p>
            <p className="mt-1 text-[10px] uppercase tracking-wider">
              Delivered at segment {event.released_at_segment ?? "-"}
            </p>
          </article>
        ))}
      </div>
    </section>
  );
}
