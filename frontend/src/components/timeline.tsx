"use client";

import { NotificationEvent, PlaybackResponse, PlaybackStep } from "@/types/api";

interface TimelineProps {
  playback: PlaybackResponse | null;
  activeStep: PlaybackStep | null;
}

function priorityClass(priority: NotificationEvent["priority"]) {
  if (priority === "urgent") {
    return "border-coral/70 bg-coral/15 text-coral";
  }
  if (priority === "semi-urgent") {
    return "border-amber/70 bg-amber/15 text-amber";
  }
  return "border-dusk-300/60 bg-dusk-600/40 text-dusk-100";
}

export function Timeline({ playback, activeStep }: TimelineProps) {
  if (!playback) {
    return (
      <section className="rounded-2xl border border-dusk-400/30 bg-dusk-800/75 p-5 backdrop-blur-lg">
        <h2 className="text-lg font-semibold">Notification Timeline</h2>
        <p className="mt-3 text-sm text-dusk-100">
          Start playback to visualize deferred and delivered notifications along connectivity segments.
        </p>
      </section>
    );
  }

  return (
    <section className="rounded-2xl border border-dusk-400/30 bg-dusk-800/75 p-5 backdrop-blur-lg">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-lg font-semibold">Notification Timeline</h2>
        <p className="text-xs uppercase tracking-wider text-dusk-200">
          {playback.switched_route ? "Switched to better-connected route" : "Stayed on selected route"}
        </p>
      </div>

      {activeStep?.warning ? (
        <div className="mb-4 rounded-xl border border-coral/60 bg-coral/10 p-3 animate-pulse-soft">
          <p className="text-sm font-semibold text-coral">Weak-zone warning ahead</p>
          <p className="text-xs text-dusk-100">
            Weak segment in {activeStep.warning.distance_to_weak_zone_m} m, estimated length {activeStep.warning.estimated_weak_zone_length_m} m.
            Better-connected option: {activeStep.warning.better_connected_route_id}
          </p>
        </div>
      ) : null}

      <div className="mb-4 grid grid-cols-2 gap-3 text-xs text-dusk-100 sm:grid-cols-4">
        <div className="rounded-xl border border-dusk-400/35 bg-dusk-700/40 p-2">
          <p className="text-dusk-200">Initial Route</p>
          <p className="font-semibold text-dusk-50">{playback.initial_route_id}</p>
        </div>
        <div className="rounded-xl border border-dusk-400/35 bg-dusk-700/40 p-2">
          <p className="text-dusk-200">Final Route</p>
          <p className="font-semibold text-dusk-50">{playback.final_route_id}</p>
        </div>
        <div className="rounded-xl border border-dusk-400/35 bg-dusk-700/40 p-2">
          <p className="text-dusk-200">Delivered</p>
          <p className="font-semibold text-dusk-50">{playback.delivered_notifications.length}</p>
        </div>
        <div className="rounded-xl border border-dusk-400/35 bg-dusk-700/40 p-2">
          <p className="text-dusk-200">Pending</p>
          <p className="font-semibold text-dusk-50">{playback.pending_notifications.length}</p>
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
