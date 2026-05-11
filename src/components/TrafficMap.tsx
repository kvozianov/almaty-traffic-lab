"use client";

import { useEffect, useMemo, useState } from "react";
import DeckGL from "@deck.gl/react";
import { GeoJsonLayer, ScatterplotLayer } from "@deck.gl/layers";
import { TripsLayer } from "@deck.gl/geo-layers";
import { Map as MapLibre } from "@vis.gl/react-maplibre";
import type { PickingInfo } from "@deck.gl/core";
import styles from "./TrafficMap.module.css";

const CARTO_DARK_MATTER_STYLE = "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json";

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
  roadId?: string;
  osmid?: string | number;
  name?: string;
  load?: number;
  density?: number;
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

type TrafficLight = {
  coordinates: Coordinate;
  color: "red" | "yellow" | "green";
};

type TrafficRoad = {
  id: string;
  density: number;
};

type TrafficPayload = {
  lights: TrafficLight[];
  roads: TrafficRoad[];
};

type Trip = {
  path: Coordinate[];
  timestamps: number[];
};

type TripsPayload = {
  trips: Trip[];
};

type TrafficMapProps = {
  className?: string;
  mapStyle?: string;
  roadsEndpoint?: string;
  trafficEndpoint?: string;
  tripsEndpoint?: string;
};

type LoadState = "idle" | "loading" | "ready" | "empty" | "error";

const TRIP_TRAIL_LENGTH_SECONDS = 35;
const TRIP_ANIMATION_SPEED = 3;

export default function TrafficMap({
  className,
  mapStyle = CARTO_DARK_MATTER_STYLE,
  roadsEndpoint = "/api/roads",
  trafficEndpoint = "/api/traffic",
  tripsEndpoint = "/api/trips",
}: TrafficMapProps) {
  const [roads, setRoads] = useState<RoadFeatureCollection>({ type: "FeatureCollection", features: [] });
  const [traffic, setTraffic] = useState<TrafficPayload>({ lights: [], roads: [] });
  const [trips, setTrips] = useState<Trip[]>([]);
  const [currentTime, setCurrentTime] = useState(0);
  const [loadState, setLoadState] = useState<LoadState>("idle");
  const [trafficState, setTrafficState] = useState<LoadState>("idle");
  const [tripsState, setTripsState] = useState<LoadState>("idle");
  const [error, setError] = useState<string | null>(null);
  const [trafficError, setTrafficError] = useState<string | null>(null);
  const [tripsError, setTripsError] = useState<string | null>(null);
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

  useEffect(() => {
    const controller = new AbortController();

    async function loadTraffic() {
      setTrafficState("loading");
      setTrafficError(null);

      try {
        const response = await fetch(trafficEndpoint, {
          headers: { Accept: "application/json" },
          signal: controller.signal,
        });

        if (!response.ok) {
          throw new Error(`Traffic request failed: ${response.status}`);
        }

        const payload = (await response.json()) as unknown;
        const nextTraffic = normalizeTrafficPayload(payload);

        setTraffic(nextTraffic);
        setTrafficState(nextTraffic.lights.length > 0 || nextTraffic.roads.length > 0 ? "ready" : "empty");
      } catch (nextError) {
        if (controller.signal.aborted) return;
        setTraffic({ lights: [], roads: [] });
        setTrafficState("error");
        setTrafficError(nextError instanceof Error ? nextError.message : "Could not load traffic state");
      }
    }

    loadTraffic();

    return () => controller.abort();
  }, [trafficEndpoint]);

  useEffect(() => {
    const controller = new AbortController();

    async function loadTrips() {
      setTripsState("loading");
      setTripsError(null);

      try {
        const response = await fetch(tripsEndpoint, {
          headers: { Accept: "application/json" },
          signal: controller.signal,
        });

        if (!response.ok) {
          throw new Error(`Trips request failed: ${response.status}`);
        }

        const payload = (await response.json()) as unknown;
        const nextTrips = parseTripsPayload(payload).trips;

        setTrips(nextTrips);
        setCurrentTime(0);
        setTripsState(nextTrips.length > 0 ? "ready" : "empty");
      } catch (nextError) {
        if (controller.signal.aborted) return;
        setTrips([]);
        setCurrentTime(0);
        setTripsState("error");
        setTripsError(nextError instanceof Error ? nextError.message : "Could not load trips");
      }
    }

    loadTrips();

    return () => controller.abort();
  }, [tripsEndpoint]);

  const roadDensityById = useMemo(() => {
    const densityById = new Map<string, number>();

    for (const road of traffic.roads) {
      densityById.set(normalizeRoadId(road.id), clamp01(road.density));
    }

    return densityById;
  }, [traffic.roads]);

  const roadsWithTraffic = useMemo<RoadFeatureCollection>(
    () => ({
      type: "FeatureCollection",
      features: roads.features.map((feature) => {
        const density = getTrafficDensityForRoad(feature.properties, roadDensityById);

        if (density === undefined) return feature;

        return {
          ...feature,
          properties: {
            ...feature.properties,
            density,
            load: density,
          },
        };
      }),
    }),
    [roadDensityById, roads],
  );

  const roadLayer = useMemo(
    () =>
      new GeoJsonLayer({
        id: "almaty-road-graph",
        data: roadsWithTraffic,
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
          getLineColor: [roadsWithTraffic],
          getLineWidth: [roadsWithTraffic],
        },
        onHover: (info: PickingInfo) => {
          setHoveredRoad(getRoadProperties(info.object) ?? null);
        },
      }),
    [roadsWithTraffic],
  );

  const trafficLightLayer = useMemo(
    () =>
      new ScatterplotLayer<TrafficLight>({
        id: "traffic-lights",
        data: traffic.lights,
        pickable: true,
        getPosition: (light) => light.coordinates,
        getFillColor: (light) => trafficLightColor(light.color),
        getLineColor: [255, 253, 248, 230],
        getRadius: 28,
        radiusMinPixels: 5,
        radiusMaxPixels: 12,
        stroked: true,
        lineWidthMinPixels: 1,
        updateTriggers: {
          getFillColor: [traffic.lights],
        },
      }),
    [traffic.lights],
  );

  const maxTripTime = useMemo(() => {
    let maxTime = 0;

    for (const trip of trips) {
      for (const timestamp of trip.timestamps) {
        maxTime = Math.max(maxTime, timestamp);
      }
    }

    return maxTime;
  }, [trips]);

  useEffect(() => {
    if (maxTripTime <= 0) {
      return;
    }

    let frameId = 0;
    let animationStart: number | null = null;

    function animateTrips(now: number) {
      animationStart ??= now;
      const elapsedSeconds = ((now - animationStart) / 1000) * TRIP_ANIMATION_SPEED;

      setCurrentTime(elapsedSeconds % maxTripTime);
      frameId = requestAnimationFrame(animateTrips);
    }

    frameId = requestAnimationFrame(animateTrips);

    return () => cancelAnimationFrame(frameId);
  }, [maxTripTime]);

  const tripGlowLayer = useMemo(
    () =>
      new TripsLayer<Trip>({
        id: "agent-vehicle-trip-glow",
        data: trips,
        getPath: (trip) => trip.path,
        getTimestamps: (trip) => trip.timestamps,
        getColor: [72, 219, 255, 90],
        getWidth: 11,
        widthMinPixels: 5,
        widthMaxPixels: 18,
        capRounded: true,
        jointRounded: true,
        fadeTrail: true,
        trailLength: TRIP_TRAIL_LENGTH_SECONDS,
        currentTime,
        parameters: {
          depthWriteEnabled: false,
        },
        updateTriggers: {
          getPath: [trips],
          getTimestamps: [trips],
        },
      }),
    [currentTime, trips],
  );

  const tripCoreLayer = useMemo(
    () =>
      new TripsLayer<Trip>({
        id: "agent-vehicle-trip-core",
        data: trips,
        getPath: (trip) => trip.path,
        getTimestamps: (trip) => trip.timestamps,
        getColor: [164, 246, 255, 245],
        getWidth: 4,
        widthMinPixels: 2,
        widthMaxPixels: 8,
        capRounded: true,
        jointRounded: true,
        fadeTrail: true,
        trailLength: TRIP_TRAIL_LENGTH_SECONDS,
        currentTime,
        parameters: {
          depthWriteEnabled: false,
        },
        updateTriggers: {
          getPath: [trips],
          getTimestamps: [trips],
        },
      }),
    [currentTime, trips],
  );

  const statusText = useMemo(() => {
    if (loadState === "loading") return "Loading road graph from /api/roads";
    if (loadState === "empty") return "No road features returned by /api/roads";
    if (loadState === "error") return error ?? "Road graph is unavailable";
    if (trafficState === "loading") return `${roads.features.length.toLocaleString("en-US")} road segments loaded | loading traffic`;
    if (trafficState === "error") {
      return `${roads.features.length.toLocaleString("en-US")} road segments loaded | ${trafficError ?? "traffic unavailable"}`;
    }
    if (tripsState === "loading") {
      return `${roads.features.length.toLocaleString("en-US")} road segments | loading trips`;
    }
    if (tripsState === "error") {
      return `${roads.features.length.toLocaleString("en-US")} road segments | ${tripsError ?? "trips unavailable"}`;
    }
    return `${roads.features.length.toLocaleString("en-US")} road segments | ${traffic.lights.length.toLocaleString(
      "en-US",
    )} lights | ${traffic.roads.length.toLocaleString("en-US")} density updates | ${trips.length.toLocaleString(
      "en-US",
    )} trips`;
  }, [
    error,
    loadState,
    roads.features.length,
    traffic.lights.length,
    traffic.roads.length,
    trafficError,
    trafficState,
    trips.length,
    tripsError,
    tripsState,
  ]);

  return (
    <section className={[styles.shell, className].filter(Boolean).join(" ")} aria-label="Almaty traffic map">
      <DeckGL
        initialViewState={ALMATY_VIEW_STATE}
        controller
        layers={[roadLayer, tripGlowLayer, tripCoreLayer, trafficLightLayer]}
        getTooltip={({ object }) => {
          if (isTrafficLight(object)) {
            return { text: `Traffic light\n${object.color}` };
          }

          const properties = object?.properties as RoadProperties | undefined;
          if (!properties) return null;
          const name = properties.name || properties.id || "Road segment";
          const speed = properties.maxSpeedKph ? `${properties.maxSpeedKph} kph` : "speed n/a";
          const density = Number(properties.density ?? properties.load ?? 0).toFixed(2);
          return { text: `${name}\ndensity ${density} | ${speed}` };
        }}
      >
        <MapLibre
          mapStyle={mapStyle}
          reuseMaps
          attributionControl={{ compact: true }}
          style={{ width: "100%", height: "100%" }}
        />
      </DeckGL>

      <div className={styles.panel}>
        <p className={styles.eyebrow}>Almaty Traffic Lab</p>
        <h1 className={styles.title}>Road graph</h1>
        <p className={styles.meta}>Almaty center | 43.238, 76.945</p>
        {hoveredRoad ? (
          <p className={styles.meta}>
            {String(hoveredRoad.name || hoveredRoad.id || hoveredRoad.osmid || "Road")} | density{" "}
            {Number(hoveredRoad.density ?? hoveredRoad.load ?? 0).toFixed(2)}
          </p>
        ) : null}
      </div>

      <div className={[styles.status, loadState === "error" ? styles.statusError : ""].filter(Boolean).join(" ")}>
        {statusText}
      </div>
    </section>
  );
}

function parseTripsPayload(payload: unknown): TripsPayload {
  if (!payload || typeof payload !== "object") {
    throw new Error("Trips payload must be an object");
  }

  const candidate = payload as Partial<TripsPayload>;
  if (!Array.isArray(candidate.trips)) {
    throw new Error("Trips payload must include trips array");
  }

  return {
    trips: candidate.trips.map(parseTrip),
  };
}

function parseTrip(trip: unknown): Trip {
  if (!trip || typeof trip !== "object") {
    throw new Error("Trip must be an object");
  }

  const candidate = trip as Partial<Trip>;
  if (!Array.isArray(candidate.path) || !Array.isArray(candidate.timestamps)) {
    throw new Error("Trip must include path and timestamps arrays");
  }

  if (candidate.path.length < 2 || candidate.path.length !== candidate.timestamps.length) {
    throw new Error("Trip path and timestamps must have equal length of at least 2");
  }

  if (!candidate.path.every(isCoordinate)) {
    throw new Error("Trip path points must be [lng, lat] number tuples");
  }

  if (!candidate.timestamps.every((timestamp) => Number.isFinite(timestamp))) {
    throw new Error("Trip timestamps must be finite seconds");
  }

  return {
    path: candidate.path,
    timestamps: candidate.timestamps,
  };
}

function normalizeTrafficPayload(payload: unknown): TrafficPayload {
  if (!payload || typeof payload !== "object") return { lights: [], roads: [] };

  const candidate = payload as { lights?: unknown; roads?: unknown };

  return {
    lights: Array.isArray(candidate.lights) ? candidate.lights.filter(isTrafficLight) : [],
    roads: Array.isArray(candidate.roads) ? candidate.roads.flatMap(normalizeTrafficRoad) : [],
  };
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

  const load = clamp01(Number(properties?.density ?? properties?.load ?? 0));
  const red = Math.round(70 + load * 185);
  const green = Math.round(202 - load * 146);
  const blue = Math.round(118 - load * 78);

  return [red, green, blue, 225];
}

function trafficLightColor(color: TrafficLight["color"]): [number, number, number, number] {
  if (color === "red") return [232, 73, 59, 240];
  if (color === "yellow") return [244, 191, 65, 240];
  return [60, 204, 124, 240];
}

function getRoadProperties(object: unknown): RoadProperties | undefined {
  if (!object || typeof object !== "object") return undefined;

  const candidate = object as { properties?: unknown };
  if (!candidate.properties || typeof candidate.properties !== "object") return undefined;

  return candidate.properties as RoadProperties;
}

function normalizeTrafficRoad(road: unknown): TrafficRoad[] {
  if (!road || typeof road !== "object") return [];

  const candidate = road as Partial<TrafficRoad>;
  if (candidate.id === undefined) return [];

  const density = Number(candidate.density);
  if (!Number.isFinite(density)) return [];

  return [{ id: String(candidate.id), density }];
}

function isTrafficLight(light: unknown): light is TrafficLight {
  if (!light || typeof light !== "object") return false;

  const candidate = light as Partial<TrafficLight>;

  return (
    (candidate.color === "red" || candidate.color === "yellow" || candidate.color === "green") &&
    Array.isArray(candidate.coordinates) &&
    candidate.coordinates.length >= 2 &&
    candidate.coordinates.every((value) => Number.isFinite(value))
  );
}

function isCoordinate(point: unknown): point is Coordinate {
  return (
    Array.isArray(point) &&
    point.length === 2 &&
    Number.isFinite(point[0]) &&
    Number.isFinite(point[1])
  );
}

function getTrafficDensityForRoad(properties: RoadProperties, densityById: Map<string, number>): number | undefined {
  for (const key of getRoadLookupKeys(properties)) {
    const density = densityById.get(key);
    if (density !== undefined) return density;
  }

  return undefined;
}

function getRoadLookupKeys(properties: RoadProperties): string[] {
  const keys = [properties.id, properties.roadId, properties.osmid]
    .filter((value): value is string | number => value !== undefined && value !== null)
    .flatMap((value) => {
      const key = normalizeRoadId(value);
      return key.includes(",") ? [key, ...key.split(",").map((part) => normalizeRoadId(part))] : [key];
    });

  return Array.from(new Set(keys));
}

function normalizeRoadId(id: string | number): string {
  return String(id).trim();
}

function clamp01(value: number): number {
  if (!Number.isFinite(value)) return 0;
  return Math.min(Math.max(value, 0), 1);
}
