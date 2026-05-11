"use client";

import { useEffect, useMemo, useState } from "react";
import DeckGL from "@deck.gl/react";
import { GeoJsonLayer } from "@deck.gl/layers";
import { Map } from "react-map-gl/mapbox";
import type { PickingInfo } from "@deck.gl/core";
import styles from "./TrafficMap.module.css";

const ALMATY_VIEW_STATE = {
  longitude: 76.945,
  latitude: 43.238,
  zoom: 11.6,
  pitch: 38,
  bearing: -10,
};

type Coordinate = [number, number];

type RoadProperties = {
  id?: string;
  name?: string;
  load?: number;
  isOpen?: boolean;
  maxSpeedKph?: number;
  capacity?: number;
  [key: string]: unknown;
};

type LineStringFeature = {
  type: "Feature";
  geometry: {
    type: "LineString";
    coordinates: Coordinate[];
  };
  properties: RoadProperties;
};

type RoadFeatureCollection = {
  type: "FeatureCollection";
  features: LineStringFeature[];
};

type LegacyRoad = {
  id?: string;
  roadId?: string;
  name?: string;
  coords?: [number, number][];
  load?: number;
  isOpen?: boolean;
  maxSpeedKph?: number;
  capacity?: number;
};

type RoadsPayload =
  | RoadFeatureCollection
  | { type?: string; features?: unknown[]; roads?: LegacyRoad[] }
  | LegacyRoad[];

type TrafficMapProps = {
  className?: string;
  mapboxAccessToken?: string;
  mapStyle?: string;
  roadsEndpoint?: string;
};

type LoadState = "idle" | "loading" | "ready" | "empty" | "error";

export default function TrafficMap({
  className,
  mapboxAccessToken = process.env.NEXT_PUBLIC_MAPBOX_ACCESS_TOKEN,
  mapStyle = "mapbox://styles/mapbox/dark-v11",
  roadsEndpoint = "/api/roads",
}: TrafficMapProps) {
  const [roads, setRoads] = useState<RoadFeatureCollection>({ type: "FeatureCollection", features: [] });
  const [loadState, setLoadState] = useState<LoadState>("idle");
  const [error, setError] = useState<string | null>(null);
  const [hoveredRoad, setHoveredRoad] = useState<RoadProperties | null>(null);

  useEffect(() => {
    const controller = new AbortController();

    async function loadRoads() {
      setLoadState("loading");
      setError(null);

      try {
        const response = await fetch(roadsEndpoint, {
          headers: { Accept: "application/geo+json, application/json" },
          signal: controller.signal,
        });

        if (!response.ok) {
          throw new Error(`Road graph request failed: ${response.status}`);
        }

        const payload = (await response.json()) as RoadsPayload;
        const nextRoads = normalizeRoadsPayload(payload);

        setRoads(nextRoads);
        setLoadState(nextRoads.features.length > 0 ? "ready" : "empty");
      } catch (nextError) {
        if (controller.signal.aborted) return;
        setRoads({ type: "FeatureCollection", features: [] });
        setLoadState("error");
        setError(nextError instanceof Error ? nextError.message : "Could not load road graph");
      }
    }

    loadRoads();

    return () => controller.abort();
  }, [roadsEndpoint]);

  const roadLayer = useMemo(
    () =>
      new GeoJsonLayer({
        id: "almaty-road-graph",
        data: roads,
        pickable: true,
        stroked: true,
        filled: false,
        lineJointRounded: true,
        lineCapRounded: true,
        getLineColor: (feature) => roadColor(getRoadProperties(feature)),
        getLineWidth: (feature) => {
          const load = Number(getRoadProperties(feature)?.load ?? 0);
          return 2 + Math.min(Math.max(load, 0), 1.5) * 5;
        },
        lineWidthMinPixels: 1,
        lineWidthMaxPixels: 8,
        updateTriggers: {
          getLineColor: [roads],
          getLineWidth: [roads],
        },
        onHover: (info: PickingInfo) => {
          setHoveredRoad(getRoadProperties(info.object) ?? null);
        },
      }),
    [roads],
  );

  const statusText = useMemo(() => {
    if (loadState === "loading") return "Loading road graph from /api/roads";
    if (loadState === "empty") return "No road features returned by /api/roads";
    if (loadState === "error") return error ?? "Road graph is unavailable";
    return `${roads.features.length.toLocaleString("en-US")} road segments loaded`;
  }, [error, loadState, roads.features.length]);

  return (
    <section className={[styles.shell, className].filter(Boolean).join(" ")} aria-label="Almaty traffic map">
      <DeckGL
        initialViewState={ALMATY_VIEW_STATE}
        controller
        layers={[roadLayer]}
        getTooltip={({ object }) => {
          const properties = object?.properties as RoadProperties | undefined;
          if (!properties) return null;
          const name = properties.name || properties.id || "Road segment";
          const speed = properties.maxSpeedKph ? `${properties.maxSpeedKph} kph` : "speed n/a";
          const load = Number(properties.load ?? 0).toFixed(2);
          return { text: `${name}\nload ${load} | ${speed}` };
        }}
      >
        <Map
          mapboxAccessToken={mapboxAccessToken}
          mapStyle={mapStyle}
          reuseMaps
          attributionControl
          style={{ width: "100%", height: "100%" }}
        />
      </DeckGL>

      <div className={styles.panel}>
        <p className={styles.eyebrow}>Almaty Traffic Lab</p>
        <h1 className={styles.title}>Road graph</h1>
        <p className={styles.meta}>Almaty center | 43.238, 76.945</p>
        {hoveredRoad ? (
          <p className={styles.meta}>
            {String(hoveredRoad.name || hoveredRoad.id || "Road")} | load {Number(hoveredRoad.load ?? 0).toFixed(2)}
          </p>
        ) : null}
      </div>

      <div className={[styles.status, loadState === "error" ? styles.statusError : ""].filter(Boolean).join(" ")}>
        {statusText}
      </div>
    </section>
  );
}

function normalizeRoadsPayload(payload: RoadsPayload): RoadFeatureCollection {
  if (isFeatureCollection(payload)) {
    return {
      type: "FeatureCollection",
      features: payload.features.filter(isLineStringFeature).map((feature) => ({
        ...feature,
        properties: feature.properties ?? {},
      })),
    };
  }

  const roads = Array.isArray(payload) ? payload : Array.isArray(payload.roads) ? payload.roads : [];

  return {
    type: "FeatureCollection",
    features: roads
      .flatMap((road) => {
        const coordinates = normalizeLegacyCoords(road.coords);
        if (coordinates.length < 2) return [];

        const feature: LineStringFeature = {
          type: "Feature" as const,
          geometry: {
            type: "LineString" as const,
            coordinates,
          },
          properties: {
            id: road.id ?? road.roadId,
            name: road.name,
            load: road.load ?? 0,
            isOpen: road.isOpen ?? true,
            maxSpeedKph: road.maxSpeedKph,
            capacity: road.capacity,
          },
        };

        return [feature];
      }),
  };
}

function normalizeLegacyCoords(coords: LegacyRoad["coords"]): Coordinate[] {
  if (!Array.isArray(coords)) return [];

  return coords
    .filter((point): point is [number, number] => Array.isArray(point) && point.length >= 2)
    .map(([lat, lng]) => [lng, lat]);
}

function isFeatureCollection(payload: RoadsPayload): payload is RoadFeatureCollection {
  return !Array.isArray(payload) && payload?.type === "FeatureCollection" && Array.isArray(payload.features);
}

function isLineStringFeature(feature: unknown): feature is LineStringFeature {
  if (!feature || typeof feature !== "object") return false;

  const candidate = feature as Partial<LineStringFeature>;
  return (
    candidate.type === "Feature" &&
    candidate.geometry?.type === "LineString" &&
    Array.isArray(candidate.geometry.coordinates) &&
    candidate.geometry.coordinates.length >= 2
  );
}

function roadColor(properties: RoadProperties | undefined): [number, number, number, number] {
  if (properties?.isOpen === false) return [34, 34, 34, 210];

  const load = Number(properties?.load ?? 0);

  if (load >= 0.65) return [207, 63, 50, 230];
  if (load >= 0.25) return [216, 144, 36, 220];
  return [88, 106, 117, 190];
}

function getRoadProperties(object: unknown): RoadProperties | undefined {
  if (!object || typeof object !== "object") return undefined;

  const candidate = object as { properties?: unknown };
  if (!candidate.properties || typeof candidate.properties !== "object") return undefined;

  return candidate.properties as RoadProperties;
}
