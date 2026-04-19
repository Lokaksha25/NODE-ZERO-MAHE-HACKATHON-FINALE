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
  startLabel: string;
  endLabel: string;
  theme: "light" | "dark";
}

function classifyColor(classification: "weak" | "moderate" | "strong") {
  return ROUTE_COLORS[classification] ?? "#7d8aa6";
}

function NavigationArrowIcon(heading: number) {
  // Google Maps-style navigation arrow (blue teardrop pointing in direction of travel)
  return L.divIcon({
    className: "",
    html: `<div style="
      width: 36px; height: 36px;
      display: flex; align-items: center; justify-content: center;
      transform: rotate(${heading}deg);
      filter: drop-shadow(0 2px 4px rgba(0,0,0,0.3));
    ">
      <svg width="36" height="36" viewBox="0 0 36 36" fill="none" xmlns="http://www.w3.org/2000/svg">
        <circle cx="18" cy="18" r="16" fill="#4285F4" fill-opacity="0.15" stroke="#4285F4" stroke-width="1.5" stroke-opacity="0.3"/>
        <path d="M18 6 L26 26 L18 21 L10 26 Z" fill="#4285F4" stroke="#ffffff" stroke-width="1.5" stroke-linejoin="round"/>
      </svg>
    </div>`,
    iconSize: [36, 36],
    iconAnchor: [18, 18],
  });
}

function computeHeading(startLon: number, startLat: number, endLon: number, endLat: number): number {
  const dLon = ((endLon - startLon) * Math.PI) / 180;
  const lat1 = (startLat * Math.PI) / 180;
  const lat2 = (endLat * Math.PI) / 180;
  const y = Math.sin(dLon) * Math.cos(lat2);
  const x = Math.cos(lat1) * Math.sin(lat2) - Math.sin(lat1) * Math.cos(lat2) * Math.cos(dLon);
  const bearing = (Math.atan2(y, x) * 180) / Math.PI;
  return (bearing + 360) % 360;
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

export function MapView({
  routes,
  selectedRouteId,
  playbackSegmentIndex,
  startLabel,
  endLabel,
  theme,
}: MapViewProps) {
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

  const heading = useMemo(() => {
    if (!activeSegment) return 0;
    return computeHeading(
      activeSegment.start.lon, activeSegment.start.lat,
      activeSegment.end.lon, activeSegment.end.lat,
    );
  }, [activeSegment]);

  const playbackIcon = useMemo(() => NavigationArrowIcon(heading), [heading]);


  return (
    <div className="absolute inset-0 z-0 overflow-hidden">
      <MapContainer
        center={[12.7, 77.2]}
        zoom={8}
        scrollWheelZoom={false}
        className="h-full w-full"
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url={
            theme === "light"
              ? "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
              : "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
          }
        />

        <Pane name="routes" style={{ zIndex: 400 }}>
          {/* Non-selected routes first (behind) */}
          {routes
            .filter((route) => route.route_id !== selectedRouteId)
            .map((route) =>
              route.segments.map((segment) => (
                <Polyline
                  key={`${route.route_id}-${segment.index}`}
                  positions={[
                    [segment.start.lat, segment.start.lon],
                    [segment.end.lat, segment.end.lon],
                  ]}
                  pathOptions={{
                    color: "#9ca3af",
                    weight: 3,
                    opacity: 0.35,
                    lineCap: "round",
                    dashArray: "6 4",
                  }}
                />
              )),
            )}
          {/* Selected route on top */}
          {routes
            .filter((route) => route.route_id === selectedRouteId)
            .map((route) =>
              route.segments.map((segment) => (
                <Polyline
                  key={`${route.route_id}-${segment.index}`}
                  positions={[
                    [segment.start.lat, segment.start.lon],
                    [segment.end.lat, segment.end.lon],
                  ]}
                  pathOptions={{
                    color: classifyColor(segment.classification),
                    weight: 6,
                    opacity: 0.96,
                    lineCap: "round",
                  }}
                />
              )),
            )}
        </Pane>

        <Pane name="endpoints" style={{ zIndex: 500 }}>
          {selectedRoute && selectedRoute.geometry.length > 1 ? (
            <>
              <CircleMarker
                center={[selectedRoute.geometry[0].lat, selectedRoute.geometry[0].lon]}
                radius={8}
                pathOptions={{ color: "#ffffff", weight: 2, fillColor: "#6ba6d8", fillOpacity: 1 }}
              >
                <Tooltip direction="top" offset={[0, -6]} permanent>
                  {startLabel}
                </Tooltip>
              </CircleMarker>
              <CircleMarker
                center={[
                  selectedRoute.geometry[selectedRoute.geometry.length - 1].lat,
                  selectedRoute.geometry[selectedRoute.geometry.length - 1].lon,
                ]}
                radius={8}
                pathOptions={{ color: "#ffffff", weight: 2, fillColor: "#111111", fillOpacity: 1 }}
              >
                <Tooltip direction="top" offset={[0, -6]} permanent>
                  {endLabel}
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
