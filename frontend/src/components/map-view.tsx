"use client";

import { useEffect, useRef } from "react";
import maplibregl, { Map } from "maplibre-gl";

import { Route } from "@/types/api";

const ROUTE_COLORS: Record<string, string> = {
  weak: "#e14c4c",
  moderate: "#e3a008",
  strong: "#2d965d",
};

type SegmentClass = "weak" | "moderate" | "strong";

interface MapViewProps {
  routes: Route[];
  selectedRouteId: string;
  playbackSegmentIndex: number;
}

function scoreToColor(classification: SegmentClass): string {
  return ROUTE_COLORS[classification] ?? "#7d8aa6";
}

function toLineFeatures(route: Route) {
  return route.segments.map((segment) => ({
    type: "Feature",
    properties: {
      routeId: route.route_id,
      segmentIndex: segment.index,
      classification: segment.classification,
      color: scoreToColor(segment.classification),
      highlighted: route.route_id,
    },
    geometry: {
      type: "LineString",
      coordinates: [
        [segment.start.lon, segment.start.lat],
        [segment.end.lon, segment.end.lat],
      ],
    },
  }));
}

export function MapView({
  routes,
  selectedRouteId,
  playbackSegmentIndex,
}: MapViewProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<Map | null>(null);

  useEffect(() => {
    if (!containerRef.current || mapRef.current) {
      return;
    }

    const map = new maplibregl.Map({
      container: containerRef.current,
      style: {
        version: 8,
        sources: {
          osm: {
            type: "raster",
            tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
            tileSize: 256,
            attribution: "© OpenStreetMap contributors",
          },
        },
        layers: [
          {
            id: "osm",
            type: "raster",
            source: "osm",
          },
        ],
      },
      center: [77.2, 12.7],
      zoom: 8,
    });

    map.addControl(new maplibregl.NavigationControl({ visualizePitch: true }), "top-right");

    map.on("load", () => {
      map.addSource("routes", {
        type: "geojson",
        data: {
          type: "FeatureCollection",
          features: [],
        },
      });

      map.addLayer({
        id: "route-lines",
        type: "line",
        source: "routes",
        paint: {
          "line-color": ["get", "color"],
          "line-width": [
            "case",
            ["==", ["get", "routeId"], selectedRouteId],
            6,
            4,
          ],
          "line-opacity": [
            "case",
            ["==", ["get", "routeId"], selectedRouteId],
            0.95,
            0.35,
          ],
        },
      });

      map.addSource("playback", {
        type: "geojson",
        data: {
          type: "FeatureCollection",
          features: [],
        },
      });

      map.addLayer({
        id: "playback-point",
        type: "circle",
        source: "playback",
        paint: {
          "circle-radius": 8,
          "circle-color": "#ff8a3d",
          "circle-stroke-color": "#ffffff",
          "circle-stroke-width": 2,
        },
      });
    });

    mapRef.current = map;

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, [selectedRouteId]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !map.getSource("routes")) {
      return;
    }

    const features = routes.flatMap(toLineFeatures);
    const source = map.getSource("routes") as maplibregl.GeoJSONSource;
    source.setData({
      type: "FeatureCollection",
      features,
    });

    const selectedRoute = routes.find((route) => route.route_id === selectedRouteId) ?? routes[0];
    if (selectedRoute) {
      const bounds = new maplibregl.LngLatBounds();
      selectedRoute.geometry.forEach((point) => bounds.extend([point.lon, point.lat]));
      if (!bounds.isEmpty()) {
        map.fitBounds(bounds, { padding: 60, duration: 500, maxZoom: 11.5 });
      }
    }
  }, [routes, selectedRouteId]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !map.getSource("playback")) {
      return;
    }

    const selectedRoute = routes.find((route) => route.route_id === selectedRouteId);
    const activeSegment = selectedRoute?.segments.find((segment) => segment.index === playbackSegmentIndex);

    if (!activeSegment) {
      const source = map.getSource("playback") as maplibregl.GeoJSONSource;
      source.setData({ type: "FeatureCollection", features: [] });
      return;
    }

    const source = map.getSource("playback") as maplibregl.GeoJSONSource;
    source.setData({
      type: "FeatureCollection",
      features: [
        {
          type: "Feature",
          geometry: {
            type: "Point",
            coordinates: [activeSegment.end.lon, activeSegment.end.lat],
          },
          properties: {},
        },
      ],
    });
  }, [playbackSegmentIndex, routes, selectedRouteId]);

  return <div ref={containerRef} className="h-[56vh] min-h-[420px] w-full rounded-2xl border border-dusk-400/35 shadow-glass" />;
}
