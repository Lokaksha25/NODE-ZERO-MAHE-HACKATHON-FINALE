"use client";

import * as turf from "@turf/turf";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { useEffect, useMemo } from "react";
import { CircleMarker, MapContainer, Marker, Pane, Polyline, TileLayer, Tooltip, useMap } from "react-leaflet";

import { Route } from "@/types/api";

const ROUTE_COLORS: Record<string, string> = {
  weak: "#e14c4c",
  moderate: "#e3a008",
  strong: "#2d965d",
};

interface MapViewProps {
  routes: Route[];
  selectedRouteId: string;
  playbackSegmentIndex: number;
}

function classifyColor(classification: "weak" | "moderate" | "strong") {
  return ROUTE_COLORS[classification] ?? "#7d8aa6";
}

function PlaybackIcon() {
  return L.divIcon({
    className: "",
    html: '<div style="width:14px;height:14px;border-radius:9999px;background:#ff8a3d;border:2px solid #ffffff;box-shadow:0 0 0 6px rgba(255,138,61,0.25)"></div>',
    iconSize: [14, 14],
    iconAnchor: [7, 7],
  });
}

function MapViewport({ selectedRoute }: { selectedRoute: Route | null }) {
  const map = useMap();

  useEffect(() => {
    if (!selectedRoute || selectedRoute.geometry.length < 2) {
      return;
    }

    const bounds = L.latLngBounds(
      selectedRoute.geometry.map((coord) => [coord.lat, coord.lon] as [number, number]),
    );
    map.fitBounds(bounds, { padding: [30, 30], maxZoom: 12 });
  }, [map, selectedRoute]);

  return null;
}

export function MapView({ routes, selectedRouteId, playbackSegmentIndex }: MapViewProps) {
  const selectedRoute = useMemo(
    () => routes.find((route) => route.route_id === selectedRouteId) ?? routes[0] ?? null,
    [routes, selectedRouteId],
  );

  const activeSegment = useMemo(() => {
    if (!selectedRoute) {
      return null;
    }
    return selectedRoute.segments.find((segment) => segment.index === playbackSegmentIndex) ?? null;
  }, [selectedRoute, playbackSegmentIndex]);

  const distanceFromOriginKm = useMemo(() => {
    if (!selectedRoute || !activeSegment) {
      return null;
    }

    const origin = selectedRoute.geometry[0];
    const current = { lon: activeSegment.end.lon, lat: activeSegment.end.lat };

    return turf.distance(
      turf.point([origin.lon, origin.lat]),
      turf.point([current.lon, current.lat]),
      { units: "kilometers" },
    );
  }, [selectedRoute, activeSegment]);

  const playbackIcon = useMemo(() => PlaybackIcon(), []);

  return (
    <div className="overflow-hidden rounded-2xl border border-dusk-400/35 shadow-glass">
      <MapContainer
        center={[12.7, 77.2]}
        zoom={8}
        scrollWheelZoom
        className="h-[56vh] min-h-[420px] w-full"
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        <Pane name="routes" style={{ zIndex: 400 }}>
          {routes.map((route) => {
            const faded = route.route_id !== selectedRouteId;
            return route.segments.map((segment) => (
              <Polyline
                key={`${route.route_id}-${segment.index}`}
                positions={[
                  [segment.start.lat, segment.start.lon],
                  [segment.end.lat, segment.end.lon],
                ]}
                pathOptions={{
                  color: classifyColor(segment.classification),
                  weight: faded ? 3 : 6,
                  opacity: faded ? 0.35 : 0.92,
                }}
              />
            ));
          })}
        </Pane>

        <Pane name="endpoints" style={{ zIndex: 500 }}>
          {selectedRoute && selectedRoute.geometry.length > 1 ? (
            <>
              <CircleMarker
                center={[selectedRoute.geometry[0].lat, selectedRoute.geometry[0].lon]}
                radius={8}
                pathOptions={{ color: "#ffffff", weight: 2, fillColor: "#2d965d", fillOpacity: 1 }}
              >
                <Tooltip direction="top" offset={[0, -6]} permanent>
                  Start
                </Tooltip>
              </CircleMarker>
              <CircleMarker
                center={[
                  selectedRoute.geometry[selectedRoute.geometry.length - 1].lat,
                  selectedRoute.geometry[selectedRoute.geometry.length - 1].lon,
                ]}
                radius={8}
                pathOptions={{ color: "#ffffff", weight: 2, fillColor: "#e14c4c", fillOpacity: 1 }}
              >
                <Tooltip direction="top" offset={[0, -6]} permanent>
                  Destination
                </Tooltip>
              </CircleMarker>
            </>
          ) : null}

          {activeSegment ? (
            <Marker position={[activeSegment.end.lat, activeSegment.end.lon]} icon={playbackIcon}>
              <Tooltip direction="top" offset={[0, -8]}>
                Segment {activeSegment.index}
                {distanceFromOriginKm ? ` • ${distanceFromOriginKm.toFixed(1)} km from start` : ""}
              </Tooltip>
            </Marker>
          ) : null}
        </Pane>

        <MapViewport selectedRoute={selectedRoute} />
      </MapContainer>
    </div>
  );
}
