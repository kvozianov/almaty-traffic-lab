"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import DeckGL from "@deck.gl/react";
import { ColumnLayer, GeoJsonLayer, IconLayer, PolygonLayer, ScatterplotLayer } from "@deck.gl/layers";
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

const INCIDENT_ICON = {
  url:
    "data:image/svg+xml;charset=utf-8," +
    encodeURIComponent(
      `<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 64 64"><path d="M32 6 60 56H4L32 6Z" fill="white"/><path d="M32 20v18" stroke="black" stroke-width="7" stroke-linecap="round"/><circle cx="32" cy="47" r="4" fill="black"/></svg>`,
    ),
  width: 64,
  height: 64,
  anchorY: 58,
  mask: true,
};

const TRIP_TRAIL_LENGTH_SECONDS = 50;
const DEFAULT_TRIP_ANIMATION_SPEED = 3;
const DEFAULT_TRAFFIC_DENSITY = 100;
const MIN_TRAFFIC_DENSITY = 100;
const MAX_TRAFFIC_DENSITY = 5000;
const DAY_SECONDS = 24 * 60 * 60;
const TRIPS_LAYER_TARGET_OPACITY = 0.8;
const LEVEL7_COLUMN_RADIUS_METERS = 96;
const LEVEL7_VARIANT_TRIP_CAP = 1200;

type Coordinate = [number, number];
type AgentType = "car" | "truck" | "bus";
type CrossingPhase = "walk" | "clearance" | "stop";
type IncidentSeverity = "low" | "medium" | "high" | "critical";
type IncidentType = "accident" | "construction" | "closure" | "event";
type CalendarMode = "weekday" | "weekend" | "night";
type ScenarioSide = "baseline" | "variant";

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
  agentType?: AgentType;
  brakeEvents?: TripBrakeEvent[];
};

type TripsPayload = {
  trips: Trip[];
};

type TripBrakeEvent = {
  at: number;
  reason: "yield" | "pedestrian" | "signal";
  intensity: number;
};

type MapIncident = {
  id: string;
  coordinates: Coordinate;
  type: IncidentType;
  severity: IncidentSeverity;
  title: string;
  description?: string;
  roadId?: string;
  impact?: number;
  updatedAt?: string;
};

type ClosureZone = {
  id: string;
  polygon: Coordinate[];
  title: string;
  severity: IncidentSeverity;
  impact?: number;
  startsAt?: string;
  endsAt?: string;
};

type AnalyticsMetrics = {
  congestionIndex: number;
  averageTravelTimeMinutes?: number;
  throughputPerHour?: number;
  activeVehicles?: number;
  jamCount?: number;
};

type TimeSeriesPoint = {
  label: string;
  congestion: number;
  throughput?: number;
};

type Bottleneck = {
  id: string;
  name: string;
  congestion: number;
  throughput?: number;
};

type Level4Analytics = {
  metrics: AnalyticsMetrics;
  incidents: MapIncident[];
  closureZones: ClosureZone[];
  timeSeries: TimeSeriesPoint[];
  forecast: TimeSeriesPoint[];
  bottlenecks: Bottleneck[];
};

type AgentProfile = {
  type: AgentType;
  count: number;
  averageSpeedKph?: number;
  delaySeconds?: number;
  brakeEvents?: number;
};

type IntersectionPhysics = {
  id: string;
  coordinates: Coordinate;
  title: string;
  priority: "major" | "minor" | "roundabout";
  slowdownRadiusMeters: number;
  yieldDelaySeconds: number;
  activeApproachDensity: number;
};

type PedestrianCrossing = {
  id: string;
  coordinates: Coordinate;
  title: string;
  phase: CrossingPhase;
  brakeIntensity: number;
  cycleSeconds: number;
  nextSwitchSeconds?: number;
};

type Level6Physics = {
  agentProfiles: AgentProfile[];
  intersections: IntersectionPhysics[];
  pedestrianCrossings: PedestrianCrossing[];
  updatedAt?: string;
  source: "api" | "mock";
};

type CalendarPattern = {
  id: string;
  mode: CalendarMode;
  title: string;
  trafficMultiplier: number;
  attractionShift: number;
  description?: string;
};

type Level7Point = {
  id: string;
  coordinates: Coordinate;
  label: string;
  intensity: number;
  mode: CalendarMode;
};

type JamColumn = {
  id: string;
  coordinates: Coordinate;
  label: string;
  intensity: number;
  heightMeters: number;
  scenario: ScenarioSide;
  mode?: CalendarMode;
};

type ComparisonScenario = {
  id: string;
  title: string;
  baselineLabel: string;
  variantLabel: string;
  deltaCongestion: number;
  deltaTravelTimeMinutes?: number;
  blockedRoadName?: string;
  closedStreets?: string;
  status?: "ready" | "pending" | "simulating";
};

type Level7Patterns = {
  calendarPatterns: CalendarPattern[];
  attractionPoints: Level7Point[];
  jamColumns: JamColumn[];
  comparisons: ComparisonScenario[];
  updatedAt?: string;
  source: "api" | "derived" | "stub";
};

type MapSelection =
  | { kind: "road"; title: string; detail: string }
  | { kind: "incident"; title: string; detail: string }
  | { kind: "closure"; title: string; detail: string }
  | { kind: "light"; title: string; detail: string }
  | { kind: "intersection"; title: string; detail: string }
  | { kind: "crossing"; title: string; detail: string }
  | { kind: "level7"; title: string; detail: string };

type TrafficMapProps = {
  className?: string;
  mapStyle?: string;
  roadsEndpoint?: string;
  trafficEndpoint?: string;
  tripsEndpoint?: string;
  analyticsEndpoint?: string;
  analyticsExportEndpoint?: string;
  physicsEndpoint?: string;
};

type LoadState = "idle" | "loading" | "ready" | "empty" | "error";

const EMPTY_ANALYTICS: Level4Analytics = {
  metrics: { congestionIndex: 0 },
  incidents: [],
  closureZones: [],
  timeSeries: [],
  forecast: [],
  bottlenecks: [],
};

const EMPTY_LEVEL7: Level7Patterns = {
  source: "stub",
  calendarPatterns: [],
  attractionPoints: [],
  jamColumns: [],
  comparisons: [],
};

const DERIVED_LEVEL7_PATTERNS: CalendarPattern[] = [
  {
    id: "weekday",
    mode: "weekday",
    title: "Обычный день",
    trafficMultiplier: 1,
    attractionShift: 0.18,
    description: "Baseline commuter demand for workday comparison.",
  },
  {
    id: "weekend",
    mode: "weekend",
    title: "Выходной",
    trafficMultiplier: 0.72,
    attractionShift: 0.46,
    description: "Demand shifts toward malls, parks, and leisure corridors.",
  },
  {
    id: "night",
    mode: "night",
    title: "Ночь",
    trafficMultiplier: 0.28,
    attractionShift: 0.08,
    description: "Low-flow mode with isolated late congestion pockets.",
  },
];

const MOCK_LEVEL6_PHYSICS: Level6Physics = {
  source: "mock",
  updatedAt: "mock",
  agentProfiles: [
    { type: "car", count: 1280, averageSpeedKph: 32.4, delaySeconds: 42, brakeEvents: 186 },
    { type: "truck", count: 214, averageSpeedKph: 24.8, delaySeconds: 71, brakeEvents: 58 },
    { type: "bus", count: 96, averageSpeedKph: 21.6, delaySeconds: 85, brakeEvents: 37 },
  ],
  intersections: [
    {
      id: "yield-abay-seifullin",
      coordinates: [76.9394, 43.2501],
      title: "Abay / Seifullin",
      priority: "major",
      slowdownRadiusMeters: 92,
      yieldDelaySeconds: 11,
      activeApproachDensity: 0.72,
    },
    {
      id: "yield-satpaev-furmanov",
      coordinates: [76.9537, 43.2368],
      title: "Satpaev / Nazarbayev",
      priority: "minor",
      slowdownRadiusMeters: 76,
      yieldDelaySeconds: 17,
      activeApproachDensity: 0.84,
    },
    {
      id: "yield-timiryazev-auezov",
      coordinates: [76.9078, 43.2258],
      title: "Timiryazev / Auezov",
      priority: "roundabout",
      slowdownRadiusMeters: 66,
      yieldDelaySeconds: 9,
      activeApproachDensity: 0.58,
    },
  ],
  pedestrianCrossings: [
    {
      id: "crossing-panfilov-arbat",
      coordinates: [76.9458, 43.2632],
      title: "Panfilov promenade",
      phase: "walk",
      brakeIntensity: 0.78,
      cycleSeconds: 36,
      nextSwitchSeconds: 14,
    },
    {
      id: "crossing-abay-masanchi",
      coordinates: [76.9289, 43.2409],
      title: "Abay / Masanchi",
      phase: "clearance",
      brakeIntensity: 0.45,
      cycleSeconds: 42,
      nextSwitchSeconds: 8,
    },
    {
      id: "crossing-dostyk-satpaev",
      coordinates: [76.9586, 43.2361],
      title: "Dostyk / Satpaev",
      phase: "stop",
      brakeIntensity: 0.18,
      cycleSeconds: 48,
      nextSwitchSeconds: 27,
    },
  ],
};

export default function TrafficMap({
  className,
  mapStyle = CARTO_DARK_MATTER_STYLE,
  roadsEndpoint = "/api/roads",
  trafficEndpoint = "/api/traffic",
  tripsEndpoint = "/api/trips",
  analyticsEndpoint = "/api/analytics",
  analyticsExportEndpoint = "/api/analytics/export",
  physicsEndpoint = "/api/physics",
}: TrafficMapProps) {
  const [roads, setRoads] = useState<RoadFeatureCollection>({ type: "FeatureCollection", features: [] });
  const [traffic, setTraffic] = useState<TrafficPayload>({ lights: [], roads: [] });
  const [trips, setTrips] = useState<Trip[]>([]);
  const [variantTrips, setVariantTrips] = useState<Trip[]>([]);
  const [analytics, setAnalytics] = useState<Level4Analytics>(EMPTY_ANALYTICS);
  const [physics, setPhysics] = useState<Level6Physics>(MOCK_LEVEL6_PHYSICS);
  const [currentTime, setCurrentTime] = useState(0);
  const [isPlaying, setIsPlaying] = useState(true);
  const [simulationSpeed, setSimulationSpeed] = useState(DEFAULT_TRIP_ANIMATION_SPEED);
  const [trafficDensity, setTrafficDensity] = useState(DEFAULT_TRAFFIC_DENSITY);
  const [requestedTrafficDensity, setRequestedTrafficDensity] = useState(DEFAULT_TRAFFIC_DENSITY);
  const [showAgentClasses, setShowAgentClasses] = useState(true);
  const [showPhysicsOverlay, setShowPhysicsOverlay] = useState(true);
  const [showPedestrianPhases, setShowPedestrianPhases] = useState(true);
  const [showLevel7Columns, setShowLevel7Columns] = useState(true);
  const [splitScreenEnabled, setSplitScreenEnabled] = useState(false);
  const [activeCalendarMode, setActiveCalendarMode] = useState<CalendarMode>("weekday");
  const [activeComparisonId, setActiveComparisonId] = useState<string | null>(null);
  const [tripsLayerOpacity, setTripsLayerOpacity] = useState(TRIPS_LAYER_TARGET_OPACITY);
  const [loadState, setLoadState] = useState<LoadState>("idle");
  const [trafficState, setTrafficState] = useState<LoadState>("idle");
  const [tripsState, setTripsState] = useState<LoadState>("idle");
  const [variantTripsState, setVariantTripsState] = useState<LoadState>("idle");
  const [analyticsState, setAnalyticsState] = useState<LoadState>("idle");
  const [physicsState, setPhysicsState] = useState<LoadState>("idle");
  const [error, setError] = useState<string | null>(null);
  const [trafficError, setTrafficError] = useState<string | null>(null);
  const [tripsError, setTripsError] = useState<string | null>(null);
  const [variantTripsError, setVariantTripsError] = useState<string | null>(null);
  const [analyticsError, setAnalyticsError] = useState<string | null>(null);
  const [physicsError, setPhysicsError] = useState<string | null>(null);
  const [hoveredRoad, setHoveredRoad] = useState<RoadProperties | null>(null);
  const [selectedItem, setSelectedItem] = useState<MapSelection | null>(null);
  const currentTimeRef = useRef(0);
  const tripsOpacityRef = useRef(TRIPS_LAYER_TARGET_OPACITY);
  const tripsOpacityFrameRef = useRef(0);

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

  const animateTripsOpacity = useCallback((targetOpacity: number) => {
    cancelAnimationFrame(tripsOpacityFrameRef.current);

    const startOpacity = tripsOpacityRef.current;
    const startTime = performance.now();
    const durationMs = 420;

    function animate(now: number) {
      const progress = Math.min((now - startTime) / durationMs, 1);
      const easedProgress = 1 - Math.pow(1 - progress, 3);
      const nextOpacity = startOpacity + (targetOpacity - startOpacity) * easedProgress;

      tripsOpacityRef.current = nextOpacity;
      setTripsLayerOpacity(nextOpacity);

      if (progress < 1) {
        tripsOpacityFrameRef.current = requestAnimationFrame(animate);
      }
    }

    tripsOpacityFrameRef.current = requestAnimationFrame(animate);
  }, []);

  useEffect(() => {
    return () => cancelAnimationFrame(tripsOpacityFrameRef.current);
  }, []);

  useEffect(() => {
    const controller = new AbortController();

    async function loadTrips() {
      setTripsState("loading");
      setTripsError(null);
      const shouldWaitForFade = tripsOpacityRef.current > 0.3;
      animateTripsOpacity(0.2);

      try {
        const response = await fetch(
          buildTripsRequestUrl(tripsEndpoint, requestedTrafficDensity, activeCalendarMode),
          {
            headers: { Accept: "application/json" },
            signal: controller.signal,
          },
        );

        if (!response.ok) {
          throw new Error(`Trips request failed: ${response.status}`);
        }

        const payload = (await response.json()) as unknown;
        const nextTrips = parseTripsPayload(payload).trips;

        if (shouldWaitForFade) {
          await delay(180);
          if (controller.signal.aborted) return;
        }

        setTrips(nextTrips);
        setCurrentTime(0);
        currentTimeRef.current = 0;
        setTripsState(nextTrips.length > 0 ? "ready" : "empty");
        animateTripsOpacity(TRIPS_LAYER_TARGET_OPACITY);
      } catch (nextError) {
        if (controller.signal.aborted) return;
        setTrips([]);
        setCurrentTime(0);
        currentTimeRef.current = 0;
        setTripsState("error");
        setTripsError(nextError instanceof Error ? nextError.message : "Could not load trips");
        animateTripsOpacity(TRIPS_LAYER_TARGET_OPACITY);
      }
    }

    loadTrips();

    return () => controller.abort();
  }, [activeCalendarMode, animateTripsOpacity, requestedTrafficDensity, tripsEndpoint]);

  useEffect(() => {
    const controller = new AbortController();

    async function loadAnalytics() {
      setAnalyticsState("loading");
      setAnalyticsError(null);

      try {
        const response = await fetch(buildAnalyticsRequestUrl(analyticsEndpoint, activeCalendarMode), {
          headers: { Accept: "application/json" },
          signal: controller.signal,
        });

        if (response.status === 404) {
          setAnalytics(EMPTY_ANALYTICS);
          setAnalyticsState("empty");
          return;
        }

        if (!response.ok) {
          throw new Error(`Analytics request failed: ${response.status}`);
        }

        const payload = (await response.json()) as unknown;
        const nextAnalytics = normalizeAnalyticsPayload(payload);

        setAnalytics(nextAnalytics);
        setAnalyticsState(hasAnalyticsData(nextAnalytics) ? "ready" : "empty");
      } catch (nextError) {
        if (controller.signal.aborted) return;
        setAnalytics(EMPTY_ANALYTICS);
        setAnalyticsState("error");
        setAnalyticsError(nextError instanceof Error ? nextError.message : "Could not load analytics");
      }
    }

    loadAnalytics();

    return () => controller.abort();
  }, [activeCalendarMode, analyticsEndpoint]);

  useEffect(() => {
    const controller = new AbortController();

    async function loadPhysics() {
      setPhysicsState("loading");
      setPhysicsError(null);

      try {
        const response = await fetch(physicsEndpoint, {
          headers: { Accept: "application/json" },
          signal: controller.signal,
        });

        if (response.status === 404) {
          setPhysics(MOCK_LEVEL6_PHYSICS);
          setPhysicsState("empty");
          return;
        }

        if (!response.ok) {
          throw new Error(`Physics request failed: ${response.status}`);
        }

        const payload = (await response.json()) as unknown;
        const nextPhysics = normalizePhysicsPayload(payload);

        setPhysics(nextPhysics);
        setPhysicsState(hasPhysicsData(nextPhysics) ? "ready" : "empty");
      } catch (nextError) {
        if (controller.signal.aborted) return;
        setPhysics(MOCK_LEVEL6_PHYSICS);
        setPhysicsState("error");
        setPhysicsError(nextError instanceof Error ? nextError.message : "Could not load level 6 physics");
      }
    }

    loadPhysics();

    return () => controller.abort();
  }, [physicsEndpoint]);

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

  const snapshot = useMemo(
    () => buildAnalyticsSnapshot(analytics, roadsWithTraffic, trips),
    [analytics, roadsWithTraffic, trips],
  );

  const level6Snapshot = useMemo(() => buildPhysicsSnapshot(physics, trips), [physics, trips]);

  const level7Snapshot = useMemo(
    () => buildLevel7Snapshot(EMPTY_LEVEL7, roadsWithTraffic, snapshot),
    [roadsWithTraffic, snapshot],
  );

  const activeCalendarPattern = useMemo(
    () =>
      level7Snapshot.calendarPatterns.find((pattern) => pattern.mode === activeCalendarMode) ??
      DERIVED_LEVEL7_PATTERNS.find((pattern) => pattern.mode === activeCalendarMode) ??
      DERIVED_LEVEL7_PATTERNS[0],
    [activeCalendarMode, level7Snapshot.calendarPatterns],
  );

  const activeComparison = useMemo(
    () =>
      level7Snapshot.comparisons.find((comparison) => comparison.id === activeComparisonId) ??
      level7Snapshot.comparisons[0],
    [activeComparisonId, level7Snapshot.comparisons],
  );

  useEffect(() => {
    if (!splitScreenEnabled || !activeComparison?.closedStreets) {
      return;
    }

    const controller = new AbortController();

    async function loadVariantTrips() {
      setVariantTripsState("loading");
      setVariantTripsError(null);

      try {
        const response = await fetch(
          buildTripsRequestUrl(
            tripsEndpoint,
            Math.min(requestedTrafficDensity, LEVEL7_VARIANT_TRIP_CAP),
            activeCalendarMode,
            activeComparison?.closedStreets,
          ),
          {
            headers: { Accept: "application/json" },
            signal: controller.signal,
          },
        );

        if (!response.ok) {
          throw new Error(`Variant trips request failed: ${response.status}`);
        }

        const payload = (await response.json()) as unknown;
        const nextTrips = parseTripsPayload(payload).trips;

        setVariantTrips(nextTrips);
        setVariantTripsState(nextTrips.length > 0 ? "ready" : "empty");
      } catch (nextError) {
        if (controller.signal.aborted) return;
        setVariantTrips([]);
        setVariantTripsState("error");
        setVariantTripsError(nextError instanceof Error ? nextError.message : "Could not load variant trips");
      }
    }

    loadVariantTrips();

    return () => controller.abort();
  }, [
    activeCalendarMode,
    activeComparison?.closedStreets,
    requestedTrafficDensity,
    splitScreenEnabled,
    tripsEndpoint,
  ]);

  const trafficLightsWithPhase = useMemo(
    () =>
      traffic.lights.map((light, index) => ({
        ...light,
        color: cycleTrafficLightColor(light.color, currentTime, index),
      })),
    [currentTime, traffic.lights],
  );

  const physicsClockSecond = Math.floor(currentTime);

  const crossingPhases = useMemo(
    () =>
      level6Snapshot.pedestrianCrossings.map((crossing, index) => ({
        ...crossing,
        phase: cycleCrossingPhase(crossing, physicsClockSecond, index),
      })),
    [level6Snapshot.pedestrianCrossings, physicsClockSecond],
  );

  const tripsByAgentType = useMemo(() => groupTripsByAgentType(trips), [trips]);
  const variantTripsByAgentType = useMemo(() => groupTripsByAgentType(variantTrips), [variantTrips]);

  const updateHoveredRoad = useCallback((properties: RoadProperties | null) => {
    setHoveredRoad((current) => {
      const currentKey = current ? getPrimaryRoadKey(current) : null;
      const nextKey = properties ? getPrimaryRoadKey(properties) : null;

      return currentKey === nextKey ? current : properties;
    });
  }, []);

  const deckLayerNamespace = splitScreenEnabled ? "split" : "single";

  const roadLayer = useMemo(
    () =>
      new GeoJsonLayer({
        id: `${deckLayerNamespace}-almaty-road-graph`,
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
          updateHoveredRoad(getRoadProperties(info.object) ?? null);
        },
        onClick: (info: PickingInfo) => {
          const properties = getRoadProperties(info.object);
          if (!properties) return false;

          setSelectedItem({
            kind: "road",
            title: String(properties.name || properties.id || properties.osmid || "Road segment"),
            detail: `density ${formatPercent(Number(properties.density ?? properties.load ?? 0))} | ${
              properties.maxSpeedKph ? `${properties.maxSpeedKph} kph` : "speed n/a"
            }`,
          });

          return true;
        },
      }),
    [deckLayerNamespace, roadsWithTraffic, updateHoveredRoad],
  );

  const trafficLightLayer = useMemo(
    () =>
      new ScatterplotLayer<TrafficLight>({
        id: `${deckLayerNamespace}-traffic-lights`,
        data: trafficLightsWithPhase,
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
          getFillColor: [trafficLightsWithPhase],
        },
        onClick: (info) => {
          if (!isTrafficLight(info.object)) return false;

          setSelectedItem({
            kind: "light",
            title: "Traffic light",
            detail: `phase ${info.object.color}`,
          });

          return true;
        },
      }),
    [deckLayerNamespace, trafficLightsWithPhase],
  );

  const closureZoneLayer = useMemo(
    () =>
      new PolygonLayer<ClosureZone>({
        id: `${deckLayerNamespace}-level4-closure-zones`,
        data: snapshot.closureZones,
        pickable: true,
        filled: true,
        stroked: true,
        extruded: false,
        getPolygon: (zone) => zone.polygon,
        getFillColor: (zone) => closureZoneFillColor(zone.severity),
        getLineColor: (zone) => severityColor(zone.severity, 230),
        getLineWidth: (zone) => 1.5 + clamp01(zone.impact ?? 0.45) * 3,
        lineWidthMinPixels: 1,
        lineWidthMaxPixels: 5,
        parameters: {
          depthWriteEnabled: false,
        },
        updateTriggers: {
          getFillColor: [snapshot.closureZones],
          getLineColor: [snapshot.closureZones],
          getLineWidth: [snapshot.closureZones],
        },
        onClick: (info) => {
          if (!isClosureZone(info.object)) return false;

          setSelectedItem({
            kind: "closure",
            title: info.object.title,
            detail: `impact ${formatPercent(info.object.impact ?? severityToImpact(info.object.severity))}`,
          });

          return true;
        },
      }),
    [deckLayerNamespace, snapshot.closureZones],
  );

  const incidentLayer = useMemo(
    () =>
      new IconLayer<MapIncident>({
        id: `${deckLayerNamespace}-level4-incidents`,
        data: snapshot.incidents,
        pickable: true,
        billboard: true,
        getPosition: (incident) => incident.coordinates,
        getIcon: () => INCIDENT_ICON,
        getColor: (incident) => severityColor(incident.severity, 245),
        getSize: (incident) => 24 + clamp01(incident.impact ?? severityToImpact(incident.severity)) * 18,
        sizeUnits: "pixels",
        parameters: {
          depthWriteEnabled: false,
        },
        updateTriggers: {
          getColor: [snapshot.incidents],
          getSize: [snapshot.incidents],
        },
        onClick: (info) => {
          if (!isMapIncident(info.object)) return false;

          setSelectedItem({
            kind: "incident",
            title: info.object.title,
            detail: `${info.object.type} | impact ${formatPercent(
              info.object.impact ?? severityToImpact(info.object.severity),
            )}`,
          });

          return true;
        },
      }),
    [deckLayerNamespace, snapshot.incidents],
  );

  const maxTripTime = useMemo(() => {
    let maxTime = 0;

    for (const trip of trips) {
      maxTime = Math.max(maxTime, getTripEndTime(trip));
    }

    return maxTime;
  }, [trips]);

  useEffect(() => {
    currentTimeRef.current = currentTime;
  }, [currentTime]);

  useEffect(() => {
    if (maxTripTime <= 0 || !isPlaying) {
      return;
    }

    let frameId = 0;
    let previousFrameTime: number | null = null;

    function animateTrips(now: number) {
      previousFrameTime ??= now;
      const elapsedSeconds = ((now - previousFrameTime) / 1000) * simulationSpeed;
      const nextTime = (currentTimeRef.current + elapsedSeconds) % maxTripTime;

      currentTimeRef.current = nextTime;
      setCurrentTime(nextTime);
      previousFrameTime = now;
      frameId = requestAnimationFrame(animateTrips);
    }

    frameId = requestAnimationFrame(animateTrips);

    return () => cancelAnimationFrame(frameId);
  }, [isPlaying, maxTripTime, simulationSpeed]);

  const tripLayers = useMemo(
    () =>
      showAgentClasses
        ? [
            createVehicleTripLayer(
              `${deckLayerNamespace}-agent-vehicle-trips`,
              tripsByAgentType.car,
              currentTime,
              tripsLayerOpacity,
              "car",
            ),
            createVehicleTripLayer(
              `${deckLayerNamespace}-level6-truck-trips`,
              tripsByAgentType.truck,
              currentTime,
              tripsLayerOpacity,
              "truck",
            ),
            createVehicleTripLayer(
              `${deckLayerNamespace}-level6-bus-trips`,
              tripsByAgentType.bus,
              currentTime,
              tripsLayerOpacity,
              "bus",
            ),
          ]
        : [
            createVehicleTripLayer(
              `${deckLayerNamespace}-agent-vehicle-trips`,
              trips,
              currentTime,
              tripsLayerOpacity,
              "car",
            ),
          ],
    [currentTime, deckLayerNamespace, showAgentClasses, trips, tripsByAgentType, tripsLayerOpacity],
  );

  const variantTripLayers = useMemo(
    () =>
      showAgentClasses
        ? [
            createVehicleTripLayer(
              `${deckLayerNamespace}-variant-car-trips`,
              variantTripsByAgentType.car,
              currentTime,
              tripsLayerOpacity,
              "car",
            ),
            createVehicleTripLayer(
              `${deckLayerNamespace}-variant-truck-trips`,
              variantTripsByAgentType.truck,
              currentTime,
              tripsLayerOpacity,
              "truck",
            ),
            createVehicleTripLayer(
              `${deckLayerNamespace}-variant-bus-trips`,
              variantTripsByAgentType.bus,
              currentTime,
              tripsLayerOpacity,
              "bus",
            ),
          ]
        : [
            createVehicleTripLayer(
              `${deckLayerNamespace}-variant-vehicle-trips`,
              variantTrips,
              currentTime,
              tripsLayerOpacity,
              "car",
            ),
          ],
    [currentTime, deckLayerNamespace, showAgentClasses, tripsLayerOpacity, variantTrips, variantTripsByAgentType],
  );

  const intersectionSlowdownLayer = useMemo(
    () =>
      new ScatterplotLayer<IntersectionPhysics>({
        id: `${deckLayerNamespace}-level6-yield-slowdown-zones`,
        data: showPhysicsOverlay ? level6Snapshot.intersections : [],
        pickable: true,
        getPosition: (intersection) => intersection.coordinates,
        getFillColor: (intersection) => yieldZoneFillColor(intersection.activeApproachDensity),
        getLineColor: (intersection) => yieldZoneLineColor(intersection.priority),
        getRadius: (intersection) => intersection.slowdownRadiusMeters,
        radiusUnits: "meters",
        radiusMinPixels: 18,
        radiusMaxPixels: 68,
        stroked: true,
        lineWidthMinPixels: 1,
        lineWidthMaxPixels: 3,
        parameters: {
          depthWriteEnabled: false,
        },
        updateTriggers: {
          getFillColor: [level6Snapshot.intersections],
          getLineColor: [level6Snapshot.intersections],
          getRadius: [level6Snapshot.intersections],
        },
        onClick: (info) => {
          if (!isIntersectionPhysics(info.object)) return false;

          setSelectedItem({
            kind: "intersection",
            title: info.object.title,
            detail: `${intersectionPriorityLabel(info.object.priority)} | yield delay ${Math.round(
              info.object.yieldDelaySeconds,
            )}s | approach ${formatPercent(info.object.activeApproachDensity)}`,
          });

          return true;
        },
      }),
    [deckLayerNamespace, level6Snapshot.intersections, showPhysicsOverlay],
  );

  const intersectionCoreLayer = useMemo(
    () =>
      new ScatterplotLayer<IntersectionPhysics>({
        id: `${deckLayerNamespace}-level6-yield-intersection-cores`,
        data: showPhysicsOverlay ? level6Snapshot.intersections : [],
        pickable: true,
        getPosition: (intersection) => intersection.coordinates,
        getFillColor: (intersection) => yieldCoreColor(intersection.priority),
        getLineColor: [255, 253, 248, 210],
        getRadius: (intersection) => 7 + clamp01(intersection.activeApproachDensity) * 7,
        radiusUnits: "pixels",
        stroked: true,
        lineWidthMinPixels: 1,
        parameters: {
          depthWriteEnabled: false,
        },
        updateTriggers: {
          getFillColor: [level6Snapshot.intersections],
          getRadius: [level6Snapshot.intersections],
        },
        onClick: (info) => {
          if (!isIntersectionPhysics(info.object)) return false;

          setSelectedItem({
            kind: "intersection",
            title: info.object.title,
            detail: `${intersectionPriorityLabel(info.object.priority)} | slowdown radius ${Math.round(
              info.object.slowdownRadiusMeters,
            )}m`,
          });

          return true;
        },
      }),
    [deckLayerNamespace, level6Snapshot.intersections, showPhysicsOverlay],
  );

  const pedestrianCrossingLayer = useMemo(
    () =>
      new ScatterplotLayer<PedestrianCrossing>({
        id: `${deckLayerNamespace}-level6-pedestrian-crossing-phases`,
        data: showPedestrianPhases ? crossingPhases : [],
        pickable: true,
        getPosition: (crossing) => crossing.coordinates,
        getFillColor: (crossing) => crossingPhaseColor(crossing.phase, crossing.brakeIntensity),
        getLineColor: (crossing) => crossingPhaseStrokeColor(crossing.phase),
        getRadius: (crossing) => 18 + clamp01(crossing.brakeIntensity) * 34,
        radiusUnits: "meters",
        radiusMinPixels: 10,
        radiusMaxPixels: 34,
        stroked: true,
        lineWidthMinPixels: 2,
        parameters: {
          depthWriteEnabled: false,
        },
        updateTriggers: {
          getFillColor: [crossingPhases],
          getLineColor: [crossingPhases],
          getRadius: [crossingPhases],
        },
        onClick: (info) => {
          if (!isPedestrianCrossing(info.object)) return false;

          setSelectedItem({
            kind: "crossing",
            title: info.object.title,
            detail: `${crossingPhaseLabel(info.object.phase)} | brake ${formatPercent(info.object.brakeIntensity)} | cycle ${
              info.object.cycleSeconds
            }s`,
          });

          return true;
        },
      }),
    [crossingPhases, deckLayerNamespace, showPedestrianPhases],
  );

  const level7AttractionLayer = useMemo(
    () =>
      new ScatterplotLayer<Level7Point>({
        id: `${deckLayerNamespace}-level7-calendar-attraction-points`,
        data: showLevel7Columns
          ? level7Snapshot.attractionPoints.filter((point) => point.mode === activeCalendarMode)
          : [],
        pickable: true,
        getPosition: (point) => point.coordinates,
        getFillColor: (point) => calendarPointColor(point.mode, point.intensity),
        getLineColor: [255, 253, 248, 210],
        getRadius: (point) => 36 + clamp01(point.intensity) * 110,
        radiusUnits: "meters",
        radiusMinPixels: 8,
        radiusMaxPixels: 52,
        stroked: true,
        lineWidthMinPixels: 1,
        parameters: {
          depthWriteEnabled: false,
        },
        updateTriggers: {
          getFillColor: [activeCalendarMode, level7Snapshot.attractionPoints],
          getRadius: [activeCalendarMode, level7Snapshot.attractionPoints],
        },
        onClick: (info) => {
          if (!isLevel7Point(info.object)) return false;

          setSelectedItem({
            kind: "level7",
            title: info.object.label,
            detail: `${calendarModeLabel(info.object.mode)} attraction | intensity ${formatPercent(info.object.intensity)}`,
          });

          return true;
        },
      }),
    [activeCalendarMode, deckLayerNamespace, level7Snapshot.attractionPoints, showLevel7Columns],
  );

  const level7BaselineColumnLayer = useMemo(
    () =>
      createLevel7ColumnLayer(
        `${deckLayerNamespace}-level7-baseline-jam-columns`,
        showLevel7Columns
          ? level7Snapshot.jamColumns.filter(
              (column) => column.scenario === "baseline" && (!column.mode || column.mode === activeCalendarMode),
            )
          : [],
        activeCalendarMode,
        (column) => {
          setSelectedItem({
            kind: "level7",
            title: column.label,
            detail: `baseline queue stack | intensity ${formatPercent(column.intensity)} | ${Math.round(
              column.heightMeters,
            )}m`,
          });
        },
      ),
    [activeCalendarMode, deckLayerNamespace, level7Snapshot.jamColumns, showLevel7Columns],
  );

  const level7VariantColumnLayer = useMemo(
    () =>
      createLevel7ColumnLayer(
        `${deckLayerNamespace}-level7-variant-jam-columns`,
        showLevel7Columns
          ? level7Snapshot.jamColumns.filter(
              (column) => column.scenario === "variant" && (!column.mode || column.mode === activeCalendarMode),
            )
          : [],
        activeCalendarMode,
        (column) => {
          setSelectedItem({
            kind: "level7",
            title: column.label,
            detail: `variant queue stack | intensity ${formatPercent(column.intensity)} | ${Math.round(
              column.heightMeters,
            )}m`,
          });
        },
      ),
    [activeCalendarMode, deckLayerNamespace, level7Snapshot.jamColumns, showLevel7Columns],
  );

  const timeOfDaySeconds = useMemo(() => {
    if (maxTripTime <= 0) return 0;
    return Math.min(DAY_SECONDS - 1, Math.round((currentTime / maxTripTime) * (DAY_SECONDS - 1)));
  }, [currentTime, maxTripTime]);

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
    if (analyticsState === "error") {
      return `${roads.features.length.toLocaleString("en-US")} road segments | ${analyticsError ?? "analytics unavailable"}`;
    }
    if (physicsState === "error") {
      return `${roads.features.length.toLocaleString("en-US")} road segments | ${
        physicsError ?? "level 6 physics using mock fallback"
      }`;
    }
    if (variantTripsState === "error") {
      return `${roads.features.length.toLocaleString("en-US")} road segments | ${
        variantTripsError ?? "variant scenario unavailable"
      }`;
    }
    return `${roads.features.length.toLocaleString("en-US")} road segments | ${traffic.lights.length.toLocaleString(
      "en-US",
    )} lights | ${traffic.roads.length.toLocaleString("en-US")} density updates | ${trips.length.toLocaleString(
      "en-US",
    )} trips | ${analyticsState === "ready" ? "level 4 analytics online" : "waiting for level 4 analytics API"} | ${
      physicsState === "ready" ? "level 6 physics online" : "level 6 mock overlay"
    } | level 7 scenario API ${splitScreenEnabled ? `| ${variantTrips.length.toLocaleString("en-US")} variant trips` : ""}`;
  }, [
    analyticsError,
    analyticsState,
    error,
    loadState,
    physicsError,
    physicsState,
    roads.features.length,
    splitScreenEnabled,
    traffic.lights.length,
    traffic.roads.length,
    trafficError,
    trafficState,
    trips.length,
    tripsError,
    tripsState,
    variantTrips.length,
    variantTripsError,
    variantTripsState,
  ]);

  const handleReset = useCallback(() => {
    currentTimeRef.current = 0;
    setCurrentTime(0);
  }, []);

  const handleTimeScrub = useCallback(
    (timeOfDay: number) => {
      if (maxTripTime <= 0) return;

      const nextTime = (timeOfDay / (DAY_SECONDS - 1)) * maxTripTime;
      currentTimeRef.current = nextTime;
      setCurrentTime(nextTime);
    },
    [maxTripTime],
  );

  const handleTrafficDensityRefresh = useCallback(() => {
    const nextDensity = clampInteger(trafficDensity, MIN_TRAFFIC_DENSITY, MAX_TRAFFIC_DENSITY);
    setTrafficDensity(nextDensity);
    setRequestedTrafficDensity(nextDensity);
  }, [trafficDensity]);

  const handleExportCsv = useCallback(() => {
    const rows = [
      ["metric", "value"],
      ["congestion_index", String(Math.round(snapshot.metrics.congestionIndex))],
      ["average_travel_time_minutes", String(snapshot.metrics.averageTravelTimeMinutes ?? "")],
      ["throughput_per_hour", String(snapshot.metrics.throughputPerHour ?? "")],
      ["active_vehicles", String(snapshot.metrics.activeVehicles ?? "")],
      ["jam_count", String(snapshot.metrics.jamCount ?? "")],
      ["incidents", String(snapshot.incidents.length)],
      ["closure_zones", String(snapshot.closureZones.length)],
    ];
    const csv = rows.map((row) => row.map(escapeCsvCell).join(",")).join("\n");
    const url = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
    const link = document.createElement("a");

    link.href = url;
    link.download = "almaty-traffic-level-4.csv";
    link.click();
    URL.revokeObjectURL(url);
  }, [snapshot]);

  const handleExportBackendCsv = useCallback(() => {
    window.location.href = analyticsExportEndpoint;
  }, [analyticsExportEndpoint]);

  const handleExportPdf = useCallback(() => {
    window.print();
  }, []);

  const sharedDeckLayers = useMemo(
    () => [
      roadLayer,
      ...tripLayers,
      trafficLightLayer,
      closureZoneLayer,
      incidentLayer,
      intersectionSlowdownLayer,
      intersectionCoreLayer,
      pedestrianCrossingLayer,
      level7AttractionLayer,
    ],
    [
      closureZoneLayer,
      incidentLayer,
      intersectionCoreLayer,
      intersectionSlowdownLayer,
      level7AttractionLayer,
      pedestrianCrossingLayer,
      roadLayer,
      trafficLightLayer,
      tripLayers,
    ],
  );

  const primaryDeckLayers = useMemo(
    () => [...sharedDeckLayers, level7BaselineColumnLayer, level7VariantColumnLayer],
    [level7BaselineColumnLayer, level7VariantColumnLayer, sharedDeckLayers],
  );

  const baselineDeckLayers = useMemo(
    () => [...sharedDeckLayers, level7BaselineColumnLayer],
    [level7BaselineColumnLayer, sharedDeckLayers],
  );

  const variantDeckLayers = useMemo(
    () => [...variantTripLayers, level7VariantColumnLayer],
    [level7VariantColumnLayer, variantTripLayers],
  );

  return (
    <section className={[styles.shell, className].filter(Boolean).join(" ")} aria-label="Almaty traffic map">
      <div className={splitScreenEnabled ? styles.splitMapStage : styles.mapStage}>
        <div className={styles.mapPane}>
          <DeckGL
            initialViewState={ALMATY_VIEW_STATE}
            controller
            layers={splitScreenEnabled ? baselineDeckLayers : primaryDeckLayers}
            getTooltip={({ object }) => buildTooltip(object)}
            style={{ position: "relative", width: "100%", height: "100%" }}
          >
            <MapLibre
              mapStyle={mapStyle}
              reuseMaps={!splitScreenEnabled}
              attributionControl={{ compact: true }}
              style={{ width: "100%", height: "100%" }}
            />
          </DeckGL>
          {splitScreenEnabled ? (
            <span className={styles.mapBadge}>{activeComparison?.baselineLabel ?? "Baseline"}</span>
          ) : null}
        </div>

        {splitScreenEnabled ? (
          <div className={styles.mapPane}>
            <DeckGL
              initialViewState={{ ...ALMATY_VIEW_STATE, longitude: ALMATY_VIEW_STATE.longitude + 0.006 }}
              controller
              layers={variantDeckLayers}
              getTooltip={({ object }) => buildTooltip(object)}
              style={{ position: "relative", width: "100%", height: "100%" }}
            >
              <MapLibre
                mapStyle={mapStyle}
                reuseMaps={false}
                attributionControl={{ compact: true }}
                style={{ width: "100%", height: "100%" }}
              />
            </DeckGL>
            <span className={styles.mapBadge}>{activeComparison?.variantLabel ?? "Variant"}</span>
          </div>
        ) : null}
      </div>

      <div className={styles.leftRail}>
        <div className={styles.panel}>
          <p className={styles.eyebrow}>Almaty Traffic Lab</p>
          <h1 className={styles.title}>Level 7 scenario model</h1>
          <p className={styles.meta}>Calendar demand, split-screen A/B, physical queue stacks</p>
          {hoveredRoad ? (
            <p className={styles.meta}>
              {String(hoveredRoad.name || hoveredRoad.id || hoveredRoad.osmid || "Road")} | density{" "}
              {Number(hoveredRoad.density ?? hoveredRoad.load ?? 0).toFixed(2)}
            </p>
          ) : null}
        </div>

        <aside className={styles.level7Panel} aria-label="Level 7 scenario controls">
          <div className={styles.panelHeader}>
            <span>Level 7</span>
            <small>{splitScreenEnabled && variantTripsState === "loading" ? "loading A/B" : "Jules API"}</small>
          </div>

          <div className={styles.segmentedControl} aria-label="Calendar pattern">
            {(["weekday", "weekend", "night"] as CalendarMode[]).map((mode) => (
              <button
                key={mode}
                type="button"
                className={activeCalendarMode === mode ? styles.activeControl : undefined}
                onClick={() => setActiveCalendarMode(mode)}
                aria-pressed={activeCalendarMode === mode}
              >
                {calendarModeLabel(mode)}
              </button>
            ))}
          </div>

          <div className={styles.patternCard}>
            <span>{activeCalendarPattern.title}</span>
            <strong>{formatPercent(activeCalendarPattern.trafficMultiplier)}</strong>
            <p>{activeCalendarPattern.description ?? "Waiting for calendar demand profile."}</p>
          </div>

          <div className={styles.toggleGrid}>
            <ToggleControl checked={showLevel7Columns} label="3D queues" onChange={setShowLevel7Columns} />
            <ToggleControl checked={splitScreenEnabled} label="Split view" onChange={setSplitScreenEnabled} />
          </div>

          <label className={styles.selectField}>
            <span>A/B scenario</span>
            <select
              value={activeComparison?.id ?? ""}
              onChange={(event) => setActiveComparisonId(event.currentTarget.value || null)}
            >
              {level7Snapshot.comparisons.length === 0 ? <option value="">Awaiting API</option> : null}
              {level7Snapshot.comparisons.map((comparison) => (
                <option key={comparison.id} value={comparison.id}>
                  {comparison.title}
                </option>
              ))}
            </select>
          </label>

          <div className={styles.physicsGrid}>
            <Metric label="Queue stacks" value={String(level7Snapshot.jamColumns.length)} />
            <Metric label="Attractors" value={String(level7Snapshot.attractionPoints.length)} />
            <Metric label="A/B delta" value={formatSignedPercent(activeComparison?.deltaCongestion ?? 0)} />
            <Metric label="Shift" value={formatPercent(activeCalendarPattern.attractionShift)} />
          </div>

          {variantTripsState === "error" ? <p className={styles.emptyText}>{variantTripsError}</p> : null}
        </aside>
      </div>

      <div className={styles.rightRail}>
      <aside className={styles.dashboard} aria-label="Level 4 analytics dashboard">
        <div className={styles.metricHero}>
          <span className={styles.metricLabel}>Congestion index</span>
          <strong className={styles.metricValue}>{Math.round(snapshot.metrics.congestionIndex)}</strong>
          <span className={styles.metricUnit}>/ 100</span>
        </div>

        <div className={styles.metricGrid}>
          <Metric label="Avg trip" value={formatMinutes(snapshot.metrics.averageTravelTimeMinutes)} />
          <Metric
            label={snapshot.metrics.activeVehicles === undefined ? "Throughput" : "Vehicles"}
            value={
              snapshot.metrics.activeVehicles === undefined
                ? formatThroughput(snapshot.metrics.throughputPerHour)
                : snapshot.metrics.activeVehicles.toLocaleString("en-US")
            }
          />
          <Metric label="Jams" value={String(snapshot.metrics.jamCount ?? 0)} />
          <Metric label="Events" value={String(snapshot.incidents.length + snapshot.closureZones.length)} />
        </div>

        <section className={styles.chartBlock} aria-label="Traffic over time">
          <div className={styles.panelHeader}>
            <span>Time curve</span>
            <small>{snapshot.timeSeries.length > 0 ? "history" : "derived"}</small>
          </div>
          <MiniBarChart points={snapshot.timeSeries} />
        </section>

        <section className={styles.forecastBlock} aria-label="Next hour forecast">
          <div className={styles.panelHeader}>
            <span>Next hour</span>
            <small>ML forecast</small>
          </div>
          {snapshot.forecast.length > 0 ? (
            <div className={styles.forecastList}>
              {snapshot.forecast.slice(0, 4).map((point) => (
                <span key={`${point.label}-${point.congestion}`}>
                  {point.label}
                  <b>{Math.round(point.congestion)}</b>
                </span>
              ))}
            </div>
          ) : (
            <p className={styles.emptyText}>Forecast slot ready for Jules API.</p>
          )}
        </section>

        <section className={styles.bottleneckBlock} aria-label="Top bottlenecks">
          <div className={styles.panelHeader}>
            <span>Bottlenecks</span>
            <small>top nodes</small>
          </div>
          {snapshot.bottlenecks.length > 0 ? (
            <ol className={styles.bottleneckList}>
              {snapshot.bottlenecks.slice(0, 3).map((bottleneck) => (
                <li key={bottleneck.id}>
                  <span>{bottleneck.name}</span>
                  <b>{Math.round(bottleneck.congestion)}</b>
                </li>
              ))}
            </ol>
          ) : (
            <p className={styles.emptyText}>Node capacity data pending.</p>
          )}
        </section>
      </aside>

      <aside className={styles.microPanel} aria-label="Level 6 physics controls">
        <div className={styles.panelHeader}>
          <span>Micro-model</span>
          <small>
            {physicsState === "ready" ? "API" : physicsState === "loading" ? "loading" : `${level6Snapshot.source} data`}
          </small>
        </div>

        <div className={styles.toggleGrid}>
          <ToggleControl checked={showAgentClasses} label="Agent classes" onChange={setShowAgentClasses} />
          <ToggleControl checked={showPhysicsOverlay} label="Yield zones" onChange={setShowPhysicsOverlay} />
          <ToggleControl checked={showPedestrianPhases} label="Crossings" onChange={setShowPedestrianPhases} />
        </div>

        <div className={styles.agentMix} aria-label="Agent mix">
          {level6Snapshot.agentProfiles.map((profile) => (
            <div key={profile.type} className={styles.agentRow}>
              <span
                className={styles.agentSwatch}
                style={{ background: agentCssColor(profile.type) }}
                aria-hidden="true"
              />
              <div>
                <strong>{agentTypeLabel(profile.type)}</strong>
                <small>
                  {profile.count.toLocaleString("en-US")} units
                  {profile.averageSpeedKph ? ` | ${profile.averageSpeedKph.toFixed(1)} kph` : ""}
                </small>
              </div>
              <b>{profile.delaySeconds === undefined ? "n/a" : `${Math.round(profile.delaySeconds)}s`}</b>
            </div>
          ))}
        </div>

        <div className={styles.physicsGrid}>
          <Metric label="Yield nodes" value={String(level6Snapshot.intersections.length)} />
          <Metric label="Ped phases" value={String(level6Snapshot.pedestrianCrossings.length)} />
          <Metric label="Brake load" value={formatPercent(averageCrossingBrake(level6Snapshot.pedestrianCrossings))} />
          <Metric label="Delay" value={`${Math.round(averageYieldDelay(level6Snapshot.intersections))}s`} />
        </div>

        {physicsState === "error" ? <p className={styles.emptyText}>{physicsError}</p> : null}
      </aside>
      </div>

      <div className={styles.controls} aria-label="Simulation controls">
        <div className={styles.controlHeader}>
          <div>
            <p className={styles.eyebrow}>Level 5 controls</p>
            <strong>Simulation deck</strong>
          </div>
          <span className={styles.controlTime}>{formatTimeOfDay(timeOfDaySeconds)}</span>
        </div>

        <div className={styles.playbackGroup} aria-label="Playback controls">
          <button
            type="button"
            className={isPlaying ? styles.activeControl : undefined}
            onClick={() => setIsPlaying(true)}
            aria-pressed={isPlaying}
          >
            Play
          </button>
          <button
            type="button"
            className={!isPlaying ? styles.activeControl : undefined}
            onClick={() => setIsPlaying(false)}
            aria-pressed={!isPlaying}
          >
            Pause
          </button>
          <button type="button" onClick={handleReset}>
            Reset
          </button>
        </div>

        <div className={styles.controlGrid}>
          <label className={styles.controlField}>
            <span>
              Speed
              <b>{simulationSpeed.toFixed(1)}x</b>
            </span>
            <input
              type="range"
              min="0.1"
              max="10"
              step="0.1"
              value={simulationSpeed}
              onInput={(event) => setSimulationSpeed(Number(event.currentTarget.value))}
              onChange={(event) => setSimulationSpeed(Number(event.target.value))}
            />
          </label>

          <label className={styles.controlField}>
            <span>
              Time machine
              <b>{formatTimeOfDay(timeOfDaySeconds)}</b>
            </span>
            <input
              type="range"
              min="0"
              max={DAY_SECONDS - 1}
              step="300"
              value={timeOfDaySeconds}
              disabled={maxTripTime <= 0}
              onInput={(event) => handleTimeScrub(Number(event.currentTarget.value))}
              onChange={(event) => handleTimeScrub(Number(event.target.value))}
            />
          </label>

          <label className={styles.controlField}>
            <span>
              Количество машин
              <b>{trafficDensity.toLocaleString("en-US")}</b>
            </span>
            <input
              type="range"
              min={MIN_TRAFFIC_DENSITY}
              max={MAX_TRAFFIC_DENSITY}
              step="100"
              value={trafficDensity}
              onInput={(event) => setTrafficDensity(Number(event.currentTarget.value))}
              onChange={(event) => setTrafficDensity(Number(event.target.value))}
            />
          </label>
        </div>

        <div className={styles.controlFooter}>
          <button
            type="button"
            className={styles.refreshButton}
            onClick={handleTrafficDensityRefresh}
            disabled={tripsState === "loading" || trafficDensity === requestedTrafficDensity}
          >
            {tripsState === "loading" ? "Updating" : "Обновить"}
          </button>
          <span>
            {trips.length.toLocaleString("en-US")} active routes
            {tripsState === "loading" ? " | refreshing" : ""}
          </span>
        </div>

        <div className={styles.exportGroup} aria-label="Export controls">
          <button type="button" onClick={analyticsState === "ready" ? handleExportBackendCsv : handleExportCsv}>
            CSV
          </button>
          <button type="button" onClick={handleExportPdf}>
            PDF
          </button>
        </div>
      </div>

      {selectedItem ? (
        <div className={styles.selectionPanel}>
          <span>{selectedItem.kind}</span>
          <strong>{selectedItem.title}</strong>
          <p>{selectedItem.detail}</p>
          <button type="button" onClick={() => setSelectedItem(null)} aria-label="Close selection details">
            Close
          </button>
        </div>
      ) : null}

      <div
        className={[
          styles.status,
          loadState === "error" || analyticsState === "error" || physicsState === "error" || variantTripsState === "error"
            ? styles.statusError
            : "",
        ]
          .filter(Boolean)
          .join(" ")}
      >
        {statusText}
      </div>
    </section>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className={styles.metric}>
      <span>{label}</span>
      <b>{value}</b>
    </div>
  );
}

function ToggleControl({
  checked,
  label,
  onChange,
}: {
  checked: boolean;
  label: string;
  onChange: (checked: boolean) => void;
}) {
  return (
    <label className={styles.toggleControl}>
      <input type="checkbox" checked={checked} onChange={(event) => onChange(event.currentTarget.checked)} />
      <span aria-hidden="true" />
      <b>{label}</b>
    </label>
  );
}

function MiniBarChart({ points }: { points: TimeSeriesPoint[] }) {
  if (points.length === 0) {
    return <p className={styles.emptyText}>Traffic time series will render here after the analytics API lands.</p>;
  }

  return (
    <div className={styles.bars}>
      {points.slice(-12).map((point) => (
        <span key={`${point.label}-${point.congestion}`} title={`${point.label}: ${Math.round(point.congestion)}`}>
          <i style={{ transform: `scaleY(${Math.max(0.08, clamp01(point.congestion / 100))})` }} />
          <small>{point.label}</small>
        </span>
      ))}
    </div>
  );
}

function createVehicleTripLayer(
  id: string,
  data: Trip[],
  currentTime: number,
  opacity: number,
  agentType: AgentType,
) {
  return new TripsLayer<Trip>({
    id,
    data,
    getPath: (trip) => trip.path,
    getTimestamps: (trip) => trip.timestamps,
    getColor: agentTripColor(agentType),
    getWidth: agentType === "car" ? 5 : agentType === "truck" ? 8 : 7,
    opacity,
    widthMinPixels: agentType === "car" ? 2.5 : 4,
    widthMaxPixels: agentType === "car" ? 10 : 16,
    capRounded: true,
    jointRounded: true,
    fadeTrail: true,
    trailLength: agentType === "car" ? TRIP_TRAIL_LENGTH_SECONDS : TRIP_TRAIL_LENGTH_SECONDS * 1.25,
    currentTime,
    parameters: {
      depthWriteEnabled: false,
    },
    updateTriggers: {
      getPath: [data],
      getTimestamps: [data],
    },
  });
}

function createLevel7ColumnLayer(
  id: string,
  data: JamColumn[],
  activeMode: CalendarMode,
  onSelect: (column: JamColumn) => void,
) {
  return new ColumnLayer<JamColumn>({
    id,
    data,
    pickable: true,
    diskResolution: 18,
    radius: LEVEL7_COLUMN_RADIUS_METERS,
    extruded: true,
    filled: true,
    stroked: true,
    getPosition: (column) => column.coordinates,
    getElevation: (column) => Math.max(12, column.heightMeters),
    getFillColor: (column) => level7ColumnColor(column, activeMode),
    getLineColor: [255, 253, 248, 120],
    lineWidthMinPixels: 1,
    material: false,
    parameters: {
      depthWriteEnabled: true,
    },
    updateTriggers: {
      getElevation: [data],
      getFillColor: [activeMode, data],
    },
    onClick: (info) => {
      if (!isJamColumn(info.object)) return false;
      onSelect(info.object);
      return true;
    },
  });
}

function groupTripsByAgentType(trips: Trip[]): Record<AgentType, Trip[]> {
  const groups: Record<AgentType, Trip[]> = {
    car: [],
    truck: [],
    bus: [],
  };

  for (const trip of trips) {
    groups[trip.agentType ?? "car"].push(trip);
  }

  return groups;
}

function averageCrossingBrake(crossings: PedestrianCrossing[]): number {
  if (crossings.length === 0) return 0;

  return crossings.reduce((total, crossing) => total + clamp01(crossing.brakeIntensity), 0) / crossings.length;
}

function averageYieldDelay(intersections: IntersectionPhysics[]): number {
  if (intersections.length === 0) return 0;

  return intersections.reduce((total, intersection) => total + intersection.yieldDelaySeconds, 0) / intersections.length;
}

function buildTripsRequestUrl(
  endpoint: string,
  count: number,
  mode: CalendarMode,
  closedStreets?: string,
): string {
  const requestUrl = new URL(endpoint, window.location.origin);

  requestUrl.searchParams.set("count", String(clampInteger(count, MIN_TRAFFIC_DENSITY, MAX_TRAFFIC_DENSITY)));
  requestUrl.searchParams.set("pattern", calendarModeToApiPattern(mode));

  if (closedStreets) {
    requestUrl.searchParams.set("closed_streets", closedStreets);
  }

  return requestUrl.toString();
}

function buildAnalyticsRequestUrl(endpoint: string, mode: CalendarMode, closedStreets?: string): string {
  const requestUrl = new URL(endpoint, window.location.origin);

  requestUrl.searchParams.set("pattern", calendarModeToApiPattern(mode));

  if (closedStreets) {
    requestUrl.searchParams.set("closed_streets", closedStreets);
  }

  return requestUrl.toString();
}

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => {
    window.setTimeout(resolve, ms);
  });
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

  const path = candidate.path as Coordinate[];
  const timestamps = candidate.timestamps as number[];

  if (path.length < 2 || path.length !== timestamps.length) {
    throw new Error("Trip path and timestamps must have equal length of at least 2");
  }

  if (!isCoordinate(path[0]) || !isCoordinate(path[path.length - 1])) {
    throw new Error("Trip path points must be [lng, lat] number tuples");
  }

  if (!Number.isFinite(timestamps[0]) || !Number.isFinite(timestamps[timestamps.length - 1])) {
    throw new Error("Trip timestamps must be finite seconds");
  }

  const source = trip as Record<string, unknown>;
  const brakeEventsSource = source.brakeEvents ?? source.brake_events;

  return {
    path,
    timestamps,
    agentType: normalizeAgentType(source.agentType ?? source.agent_type ?? source.vehicleType ?? source.vehicle_type ?? source.type),
    brakeEvents: Array.isArray(brakeEventsSource) ? brakeEventsSource.flatMap(normalizeTripBrakeEvent) : undefined,
  };
}

function normalizeTripBrakeEvent(item: unknown): TripBrakeEvent[] {
  const source = getRecord(item);
  if (!source) return [];

  const at = optionalNumber(source.at ?? source.time ?? source.timestamp ?? source.t);
  if (at === undefined) return [];

  return [
    {
      at,
      reason: normalizeBrakeReason(source.reason ?? source.type),
      intensity: optionalImpact(source.intensity ?? source.brakeIntensity ?? source.brake_intensity) ?? 0.45,
    },
  ];
}

function normalizePhysicsPayload(payload: unknown): Level6Physics {
  if (!payload || typeof payload !== "object") {
    return { ...MOCK_LEVEL6_PHYSICS, source: "api", agentProfiles: [], intersections: [], pedestrianCrossings: [] };
  }

  const root = payload as Record<string, unknown>;
  const agentProfilesSource = firstArray(
    root.agentProfiles,
    root.agent_profiles,
    root.agentMix,
    root.agent_mix,
    root.vehicleTypes,
    root.vehicle_types,
    root.vehicles,
    root.agents,
  );
  const intersectionsSource = firstArray(
    root.intersections,
    root.uncontrolledIntersections,
    root.uncontrolled_intersections,
    root.intersectionPhysics,
    root.intersection_physics,
    root.yieldZones,
    root.yield_zones,
    root.priorityNodes,
    root.priority_nodes,
  );
  const pedestrianCrossingsSource = firstArray(
    root.pedestrianCrossings,
    root.pedestrian_crossings,
    root.crossings,
    root.crosswalks,
    root.pedestrianPhases,
    root.pedestrian_phases,
  );

  return {
    source: "api",
    updatedAt: optionalString(root.updatedAt ?? root.updated_at ?? root.timestamp),
    agentProfiles: agentProfilesSource.flatMap(normalizeAgentProfile),
    intersections: intersectionsSource.flatMap(normalizeIntersectionPhysics),
    pedestrianCrossings: pedestrianCrossingsSource.flatMap(normalizePedestrianCrossing),
  };
}

function normalizeAgentProfile(item: unknown): AgentProfile[] {
  const source = getRecord(item);
  if (!source) return [];

  const type = normalizeAgentType(source.type ?? source.agentType ?? source.agent_type ?? source.vehicleType);
  const count = optionalInteger(source.count ?? source.total ?? source.vehicles ?? source.activeVehicles) ?? 0;

  return [
    {
      type,
      count,
      averageSpeedKph: optionalNumber(source.averageSpeedKph ?? source.average_speed_kph ?? source.avgSpeedKph),
      delaySeconds: optionalNumber(source.delaySeconds ?? source.delay_seconds ?? source.avgDelaySeconds),
      brakeEvents: optionalInteger(source.brakeEvents ?? source.brake_events ?? source.brakes),
    },
  ];
}

function normalizeIntersectionPhysics(item: unknown): IntersectionPhysics[] {
  const source = getRecord(item);
  if (!source) return [];

  const coordinates = normalizeCoordinate(source.coordinates ?? source.point ?? source.location);
  if (!coordinates) return [];

  const id = String(source.id ?? source.nodeId ?? source.node_id ?? `intersection-${coordinates.join("-")}`);
  const seed = coordinateSeed(coordinates);
  const isUncontrolled = source.type === "uncontrolled_intersection";

  return [
    {
      id,
      coordinates,
      title: String(source.title ?? source.name ?? source.label ?? (isUncontrolled ? "Uncontrolled intersection" : id)),
      priority: normalizeIntersectionPriority(source.priority ?? source.priorityRule ?? source.priority_rule ?? source.type),
      slowdownRadiusMeters:
        optionalNumber(source.slowdownRadiusMeters ?? source.slowdown_radius_meters ?? source.radiusMeters) ??
        Math.round(54 + seed * 42),
      yieldDelaySeconds:
        optionalNumber(source.yieldDelaySeconds ?? source.yield_delay_seconds ?? source.delaySeconds ?? source.delay) ??
        Math.round(5 + seed * 13),
      activeApproachDensity:
        optionalImpact(source.activeApproachDensity ?? source.active_approach_density ?? source.density ?? source.load) ??
        0.34 + seed * 0.5,
    },
  ];
}

function normalizePedestrianCrossing(item: unknown): PedestrianCrossing[] {
  const source = getRecord(item);
  if (!source) return [];

  const coordinates = normalizeCoordinate(source.coordinates ?? source.point ?? source.location);
  if (!coordinates) return [];

  const id = String(source.id ?? source.crossingId ?? source.crossing_id ?? `crossing-${coordinates.join("-")}`);
  const seed = coordinateSeed(coordinates);
  const phases: CrossingPhase[] = ["walk", "clearance", "stop"];

  return [
    {
      id,
      coordinates,
      title: String(source.title ?? source.name ?? source.label ?? "Pedestrian crossing"),
      phase:
        source.phase || source.pedestrianPhase || source.pedestrian_phase || source.state
          ? normalizeCrossingPhase(source.phase ?? source.pedestrianPhase ?? source.pedestrian_phase ?? source.state)
          : phases[Math.floor(seed * phases.length) % phases.length],
      brakeIntensity:
        optionalImpact(source.brakeIntensity ?? source.brake_intensity ?? source.impact ?? source.delay) ?? 0.22 + seed * 0.56,
      cycleSeconds:
        optionalNumber(source.cycleSeconds ?? source.cycle_seconds ?? source.cycle ?? source.period) ?? Math.round(32 + seed * 24),
      nextSwitchSeconds: optionalNumber(source.nextSwitchSeconds ?? source.next_switch_seconds ?? source.nextChangeSeconds),
    },
  ];
}

function normalizeTrafficPayload(payload: unknown): TrafficPayload {
  if (!payload || typeof payload !== "object") return { lights: [], roads: [] };

  const candidate = payload as { lights?: unknown; roads?: unknown };

  return {
    lights: Array.isArray(candidate.lights) ? candidate.lights.filter(isTrafficLight) : [],
    roads: Array.isArray(candidate.roads) ? candidate.roads.flatMap(normalizeTrafficRoad) : [],
  };
}

function normalizeAnalyticsPayload(payload: unknown): Level4Analytics {
  if (!payload || typeof payload !== "object") return EMPTY_ANALYTICS;

  const root = payload as Record<string, unknown>;
  const metricsSource = getRecord(root.summary) ?? getRecord(root.analytics) ?? getRecord(root.metrics) ?? root;
  const incidentsSource = firstArray(root.incidents, root.accidents, root.events);
  const zonesSource = firstArray(root.closureZones, root.closure_zones, root.closures, root.blockedZones, root.zones);
  const timeSeriesSource = firstArray(root.time_series, root.timeSeries, root.history, root.timeline, root.byHour);
  const forecastSource = firstArray(root.ml_forecast, root.forecast, root.mlForecast, root.prediction, root.nextHour);
  const bottlenecksSource = firstArray(
    root.node_throughput,
    root.bottlenecks,
    root.topIntersections,
    root.capacityNodes,
  );

  return {
    metrics: normalizeAnalyticsMetrics(metricsSource),
    incidents: incidentsSource.flatMap(normalizeIncident),
    closureZones: zonesSource.flatMap(normalizeClosureZone),
    timeSeries: timeSeriesSource.flatMap(normalizeTimeSeriesPoint),
    forecast: forecastSource.flatMap(normalizeTimeSeriesPoint),
    bottlenecks: bottlenecksSource.flatMap(normalizeBottleneck),
  };
}

function normalizeAnalyticsMetrics(source: Record<string, unknown>): AnalyticsMetrics {
  const averageTripSeconds = optionalNumber(source.average_trip_time_seconds ?? source.avg_trip_time_seconds);
  const averageTripMinutes = optionalNumber(
    source.averageTravelTimeMinutes ??
      source.average_trip_time_minutes ??
      source.avgTravelTimeMinutes ??
      source.averageTripMinutes ??
      source.avgTrip,
  );

  return {
    congestionIndex: normalizePercent(
      source.congestion_index ?? source.congestionIndex ?? source.congestion ?? source.loadIndex ?? source.cityLoad ?? source.index,
    ),
    averageTravelTimeMinutes: averageTripMinutes ?? (averageTripSeconds === undefined ? undefined : averageTripSeconds / 60),
    throughputPerHour: optionalNumber(source.throughput_per_hour ?? source.throughputPerHour ?? source.throughput ?? source.capacity),
    activeVehicles: optionalInteger(source.total_active_vehicles ?? source.activeVehicles ?? source.active_vehicles),
    jamCount: optionalInteger(source.jam_count ?? source.jamCount ?? source.congestionCount ?? source.jams),
  };
}

function normalizeIncident(item: unknown): MapIncident[] {
  const source = getRecord(item);
  if (!source) return [];

  const coordinates = normalizeCoordinate(source.coordinates ?? source.point ?? source.location);
  if (!coordinates) return [];

  const type = normalizeIncidentType(source.incidentType ?? source.incident_type ?? source.type);
  const severity = normalizeSeverity(source.severity ?? source.level ?? source.priority);

  return [
    {
      id: String(source.id ?? source.incidentId ?? source.incident_id ?? `${type}-${coordinates.join("-")}`),
      coordinates,
      type,
      severity,
      title: String(source.title ?? source.name ?? incidentTypeLabel(type)),
      description: optionalString(source.description ?? source.summary),
      roadId: optionalString(source.roadId ?? source.road_id ?? source.edgeId ?? source.edge_id),
      impact: optionalImpact(source.impact ?? source.densityImpact ?? source.density_impact ?? source.delayFactor),
      updatedAt: optionalString(source.updatedAt ?? source.updated_at ?? source.timestamp),
    },
  ];
}

function normalizeClosureZone(item: unknown): ClosureZone[] {
  const source = getRecord(item);
  if (!source) return [];

  const polygon = normalizePolygon(source.polygon ?? source.coordinates ?? source.geometry);
  if (polygon.length < 3) return [];

  const severity = normalizeSeverity(source.severity ?? source.level ?? source.priority);

  return [
    {
      id: String(source.id ?? source.zoneId ?? source.zone_id ?? `closure-${polygon[0].join("-")}`),
      polygon,
      title: String(source.title ?? source.name ?? "Closure zone"),
      severity,
      impact: optionalImpact(source.impact ?? source.load ?? source.density),
      startsAt: optionalString(source.startsAt ?? source.starts_at ?? source.startTime),
      endsAt: optionalString(source.endsAt ?? source.ends_at ?? source.endTime),
    },
  ];
}

function normalizeTimeSeriesPoint(item: unknown): TimeSeriesPoint[] {
  const source = getRecord(item);
  if (!source) return [];

  const congestion = normalizePercent(
    source.predicted_congestion ??
      source.congestion_index ??
      source.congestion ??
      source.congestionIndex ??
      source.load ??
      source.value,
  );
  const label = String(source.label ?? source.time ?? source.hour ?? source.bucket ?? "");
  const forecastOffset = optionalInteger(source.offset_hours ?? source.offsetHours);

  if (!label && forecastOffset === undefined) return [];

  return [
    {
      label: label || `+${forecastOffset}h`,
      congestion,
      throughput: optionalNumber(source.throughput ?? source.vehicles_per_hour ?? source.capacity),
    },
  ];
}

function normalizeBottleneck(item: unknown): Bottleneck[] {
  const source = getRecord(item);
  if (!source) return [];

  return [
    {
      id: String(source.id ?? source.node_id ?? source.nodeId ?? source.roadId ?? source.name ?? "bottleneck"),
      name: String(source.name ?? source.label ?? source.node_id ?? source.nodeId ?? "Intersection"),
      congestion: normalizePercent(source.congestion ?? source.load ?? source.score ?? statusToCongestion(source.status)),
      throughput: optionalNumber(source.throughput ?? source.vehicles_per_hour ?? source.capacity),
    },
  ];
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
    features: roads.flatMap((road) => {
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

function buildAnalyticsSnapshot(
  analytics: Level4Analytics,
  roadsWithTraffic: RoadFeatureCollection,
  trips: Trip[],
): Level4Analytics {
  const densities = roadsWithTraffic.features
    .map((feature) => Number(feature.properties.density ?? feature.properties.load ?? 0))
    .filter(Number.isFinite)
    .map(clamp01);
  const averageDensity =
    densities.length > 0 ? densities.reduce((total, density) => total + density, 0) / densities.length : 0;
  const jamCount = densities.filter((density) => density >= 0.72).length;
  const derivedTripMinutes = deriveAverageTripMinutes(trips);
  const derivedThroughput = trips.length > 0 ? Math.round(trips.length * 12) : undefined;
  const timeSeries =
    analytics.timeSeries.length > 0
      ? analytics.timeSeries
      : buildDerivedTimeSeries(averageDensity, analytics.metrics.congestionIndex);

  return {
    metrics: {
      congestionIndex:
        analytics.metrics.congestionIndex > 0 ? analytics.metrics.congestionIndex : Math.round(averageDensity * 100),
      averageTravelTimeMinutes: analytics.metrics.averageTravelTimeMinutes ?? derivedTripMinutes,
      throughputPerHour: analytics.metrics.throughputPerHour ?? derivedThroughput,
      activeVehicles: analytics.metrics.activeVehicles,
      jamCount: analytics.metrics.jamCount ?? jamCount,
    },
    incidents:
      analytics.incidents.length > 0 ? analytics.incidents : deriveTrafficIncidents(roadsWithTraffic.features),
    closureZones: analytics.closureZones,
    timeSeries,
    forecast: analytics.forecast,
    bottlenecks:
      analytics.bottlenecks.length > 0 ? analytics.bottlenecks : deriveBottlenecks(roadsWithTraffic.features),
  };
}

function buildPhysicsSnapshot(physics: Level6Physics, trips: Trip[]): Level6Physics {
  return {
    ...physics,
    agentProfiles:
      physics.agentProfiles.length > 0 ? normalizeAgentProfilesTotal(physics.agentProfiles) : deriveAgentProfiles(trips),
    intersections: physics.intersections.length > 0 ? physics.intersections : MOCK_LEVEL6_PHYSICS.intersections,
    pedestrianCrossings:
      physics.pedestrianCrossings.length > 0 ? physics.pedestrianCrossings : MOCK_LEVEL6_PHYSICS.pedestrianCrossings,
  };
}

function buildLevel7Snapshot(
  level7: Level7Patterns,
  roadsWithTraffic: RoadFeatureCollection,
  analytics: Level4Analytics,
): Level7Patterns {
  const hasApiData = hasLevel7Data(level7);
  const calendarPatterns =
    level7.calendarPatterns.length > 0 ? mergeCalendarPatterns(level7.calendarPatterns) : DERIVED_LEVEL7_PATTERNS;
  const jamColumns =
    level7.jamColumns.length > 0 ? level7.jamColumns : deriveJamColumns(roadsWithTraffic.features, analytics);
  const attractionPoints =
    level7.attractionPoints.length > 0 ? level7.attractionPoints : deriveAttractionPoints(jamColumns);
  const comparisons = level7.comparisons.length > 0 ? level7.comparisons : deriveComparisons(analytics);

  return {
    ...level7,
    source: hasApiData ? level7.source : "derived",
    calendarPatterns,
    attractionPoints,
    jamColumns,
    comparisons,
  };
}

function mergeCalendarPatterns(patterns: CalendarPattern[]): CalendarPattern[] {
  const byMode = new Map<CalendarMode, CalendarPattern>();

  for (const pattern of DERIVED_LEVEL7_PATTERNS) {
    byMode.set(pattern.mode, pattern);
  }

  for (const pattern of patterns) {
    byMode.set(pattern.mode, pattern);
  }

  return (["weekday", "weekend", "night"] as CalendarMode[]).map((mode) => byMode.get(mode) ?? DERIVED_LEVEL7_PATTERNS[0]);
}

function deriveJamColumns(features: LineStringFeature[], analytics: Level4Analytics): JamColumn[] {
  const fromRoads = features
    .flatMap((feature) => {
      const density = clamp01(Number(feature.properties.density ?? feature.properties.load ?? 0));
      const coordinates = getFeatureMidpoint(feature);

      if (!coordinates || density < 0.66) return [];

      const label = String(feature.properties.name ?? feature.properties.id ?? feature.properties.osmid ?? "Queue stack");
      const heightMeters = Math.round(36 + density * 210);

      return [
        {
          id: `baseline-${getPrimaryRoadKey(feature.properties) || coordinates.join("-")}`,
          coordinates,
          label,
          intensity: density,
          heightMeters,
          scenario: "baseline" as const,
        },
        {
          id: `variant-${getPrimaryRoadKey(feature.properties) || coordinates.join("-")}`,
          coordinates: offsetCoordinate(coordinates, 34, -28),
          label: `${label} variant`,
          intensity: clamp01(density * 0.86),
          heightMeters: Math.round(heightMeters * 0.86),
          scenario: "variant" as const,
        },
      ];
    })
    .sort((a, b) => b.intensity - a.intensity)
    .slice(0, 18);

  if (fromRoads.length > 0) return fromRoads;

  return analytics.bottlenecks.slice(0, 4).flatMap((bottleneck, index) => {
    const seed = coordinateSeed([76.91 + index * 0.016, 43.224 + index * 0.01]);
    const coordinates: Coordinate = [76.91 + index * 0.018 + seed * 0.01, 43.226 + index * 0.009];
    const intensity = clamp01(bottleneck.congestion / 100);

    return [
      {
        id: `derived-baseline-${bottleneck.id}`,
        coordinates,
        label: bottleneck.name,
        intensity,
        heightMeters: Math.round(32 + intensity * 190),
        scenario: "baseline" as const,
      },
      {
        id: `derived-variant-${bottleneck.id}`,
        coordinates: offsetCoordinate(coordinates, 40, -22),
        label: `${bottleneck.name} variant`,
        intensity: clamp01(intensity * 0.82),
        heightMeters: Math.round((32 + intensity * 190) * 0.82),
        scenario: "variant" as const,
      },
    ];
  });
}

function deriveAttractionPoints(columns: JamColumn[]): Level7Point[] {
  const topColumns = columns.filter((column) => column.scenario === "baseline").slice(0, 5);

  return topColumns.flatMap((column, index) => {
    const mode: CalendarMode = index % 3 === 0 ? "weekday" : index % 3 === 1 ? "weekend" : "night";

    return [
      {
        id: `derived-attractor-${column.id}`,
        coordinates: offsetCoordinate(column.coordinates, 90 - index * 18, 58 + index * 11),
        label: calendarAttractorLabel(mode, index),
        intensity: clamp01(column.intensity * (mode === "night" ? 0.52 : mode === "weekend" ? 0.74 : 0.9)),
        mode,
      },
    ];
  });
}

function deriveComparisons(analytics: Level4Analytics): ComparisonScenario[] {
  const congestion = analytics.metrics.congestionIndex;
  const variantDelta = congestion > 0 ? -Math.min(22, Math.max(6, congestion * 0.18)) : -12;

  return [
    {
      id: "normal-vs-abay-closure",
      title: "Обычный день vs Абая закрыта",
      baselineLabel: "Обычный день",
      variantLabel: "Абая закрыта",
      deltaCongestion: Math.abs(variantDelta),
      deltaTravelTimeMinutes: analytics.metrics.averageTravelTimeMinutes
        ? Math.round(analytics.metrics.averageTravelTimeMinutes * 0.18 * 10) / 10
        : undefined,
      blockedRoadName: "Abay avenue",
      closedStreets: "abay",
      status: "pending",
    },
    {
      id: "adaptive-signals",
      title: "Fixed lights vs adaptive",
      baselineLabel: "Fixed lights",
      variantLabel: "Adaptive policy",
      deltaCongestion: variantDelta,
      deltaTravelTimeMinutes: analytics.metrics.averageTravelTimeMinutes
        ? -Math.round(analytics.metrics.averageTravelTimeMinutes * 0.12 * 10) / 10
        : undefined,
      status: "pending",
    },
  ];
}

function normalizeAgentProfilesTotal(profiles: AgentProfile[]): AgentProfile[] {
  const merged = new Map<AgentType, AgentProfile>();

  for (const profile of profiles) {
    const current = merged.get(profile.type);
    if (!current) {
      merged.set(profile.type, profile);
      continue;
    }

    merged.set(profile.type, {
      type: profile.type,
      count: current.count + profile.count,
      averageSpeedKph: weightedAverage(current.averageSpeedKph, current.count, profile.averageSpeedKph, profile.count),
      delaySeconds: weightedAverage(current.delaySeconds, current.count, profile.delaySeconds, profile.count),
      brakeEvents: (current.brakeEvents ?? 0) + (profile.brakeEvents ?? 0),
    });
  }

  return ensureAgentProfileOrder(Array.from(merged.values()));
}

function deriveAgentProfiles(trips: Trip[]): AgentProfile[] {
  if (trips.length === 0) return MOCK_LEVEL6_PHYSICS.agentProfiles;

  const grouped = groupTripsByAgentType(trips);

  return ensureAgentProfileOrder(
    (["car", "truck", "bus"] as AgentType[]).map((type) => {
      const agentTrips = grouped[type];
      const brakeEvents = agentTrips.reduce((total, trip) => total + (trip.brakeEvents?.length ?? 0), 0);

      return {
        type,
        count: agentTrips.length,
        averageSpeedKph: deriveAverageSpeedKph(agentTrips),
        delaySeconds: brakeEvents > 0 ? 24 + brakeEvents / Math.max(1, agentTrips.length) : undefined,
        brakeEvents,
      };
    }),
  );
}

function ensureAgentProfileOrder(profiles: AgentProfile[]): AgentProfile[] {
  const byType = new Map(profiles.map((profile) => [profile.type, profile]));

  return (["car", "truck", "bus"] as AgentType[]).map(
    (type) => byType.get(type) ?? { type, count: 0, brakeEvents: 0 },
  );
}

function weightedAverage(
  leftValue: number | undefined,
  leftWeight: number,
  rightValue: number | undefined,
  rightWeight: number,
): number | undefined {
  if (leftValue === undefined) return rightValue;
  if (rightValue === undefined) return leftValue;

  const totalWeight = Math.max(1, leftWeight + rightWeight);
  return (leftValue * leftWeight + rightValue * rightWeight) / totalWeight;
}

function deriveAverageSpeedKph(trips: Trip[]): number | undefined {
  const speeds = trips
    .map((trip) => {
      const durationSeconds = trip.timestamps[trip.timestamps.length - 1] - trip.timestamps[0];
      if (!Number.isFinite(durationSeconds) || durationSeconds <= 0) return undefined;

      return (estimatePathDistanceMeters(trip.path) / durationSeconds) * 3.6;
    })
    .filter((speed): speed is number => speed !== undefined && Number.isFinite(speed));

  if (speeds.length === 0) return undefined;

  return speeds.reduce((total, speed) => total + speed, 0) / speeds.length;
}

function estimatePathDistanceMeters(path: Coordinate[]): number {
  let total = 0;

  for (let index = 1; index < path.length; index += 1) {
    total += estimateCoordinateDistanceMeters(path[index - 1], path[index]);
  }

  return total;
}

function estimateCoordinateDistanceMeters(a: Coordinate, b: Coordinate): number {
  const metersPerDegreeLat = 111_320;
  const averageLat = ((a[1] + b[1]) / 2 / 180) * Math.PI;
  const metersPerDegreeLng = metersPerDegreeLat * Math.cos(averageLat);
  const dx = (b[0] - a[0]) * metersPerDegreeLng;
  const dy = (b[1] - a[1]) * metersPerDegreeLat;

  return Math.sqrt(dx * dx + dy * dy);
}

function buildTooltip(object: unknown) {
  if (isJamColumn(object)) {
    return {
      text: `${object.label}\n${object.scenario} queue | ${formatPercent(object.intensity)}`,
    };
  }

  if (isLevel7Point(object)) {
    return {
      text: `${object.label}\n${calendarModeLabel(object.mode)} | ${formatPercent(object.intensity)}`,
    };
  }

  if (isIntersectionPhysics(object)) {
    return {
      text: `${object.title}\n${intersectionPriorityLabel(object.priority)} | yield delay ${Math.round(
        object.yieldDelaySeconds,
      )}s`,
    };
  }

  if (isPedestrianCrossing(object)) {
    return {
      text: `${object.title}\n${crossingPhaseLabel(object.phase)} | brake ${formatPercent(object.brakeIntensity)}`,
    };
  }

  if (isMapIncident(object)) {
    return {
      text: `${object.title}\n${object.type} | impact ${formatPercent(
        object.impact ?? severityToImpact(object.severity),
      )}`,
    };
  }

  if (isClosureZone(object)) {
    return {
      text: `${object.title}\nclosure impact ${formatPercent(object.impact ?? severityToImpact(object.severity))}`,
    };
  }

  if (isTrafficLight(object)) {
    return { text: `Traffic light\n${object.color}` };
  }

  const properties = getRoadProperties(object);
  if (!properties) return null;
  const name = properties.name || properties.id || "Road segment";
  const speed = properties.maxSpeedKph ? `${properties.maxSpeedKph} kph` : "speed n/a";
  const density = Number(properties.density ?? properties.load ?? 0).toFixed(2);

  return { text: `${name}\ndensity ${density} | ${speed}` };
}

function buildDerivedTimeSeries(averageDensity: number, congestionIndex: number): TimeSeriesPoint[] {
  const base = congestionIndex > 0 ? congestionIndex : averageDensity * 100;
  const labels = ["06", "08", "10", "12", "14", "16", "18", "20"];

  return labels.map((label, index) => {
    const rushHourLift = label === "08" || label === "18" ? 18 : label === "16" ? 9 : 0;
    const curve = Math.sin((index / Math.max(1, labels.length - 1)) * Math.PI) * 8;

    return {
      label,
      congestion: clampPercent(base + rushHourLift + curve - 8),
    };
  });
}

function deriveBottlenecks(features: LineStringFeature[]): Bottleneck[] {
  return features
    .map((feature, index) => ({
      id: String(feature.properties.id ?? feature.properties.osmid ?? index),
      name: String(feature.properties.name ?? feature.properties.id ?? "Road segment"),
      congestion: clampPercent(Number(feature.properties.density ?? feature.properties.load ?? 0) * 100),
      throughput: optionalNumber(feature.properties.capacity),
    }))
    .filter((item) => item.congestion > 0)
    .sort((a, b) => b.congestion - a.congestion)
    .slice(0, 5);
}

function deriveTrafficIncidents(features: LineStringFeature[]): MapIncident[] {
  return features
    .flatMap((feature) => {
      const density = clamp01(Number(feature.properties.density ?? feature.properties.load ?? 0));
      const coordinates = getFeatureMidpoint(feature);

      if (!coordinates || density < 0.9) return [];

      const title = String(
        feature.properties.name || feature.properties.id || feature.properties.osmid || "High load segment",
      );

      return [
        {
          id: `derived-incident-${getPrimaryRoadKey(feature.properties) ?? coordinates.join("-")}`,
          coordinates,
          type: density > 0.96 ? "accident" : "event",
          severity: density > 0.96 ? "critical" : "high",
          title,
          description: "Derived from live road density",
          roadId: optionalString(feature.properties.id ?? feature.properties.roadId ?? feature.properties.osmid),
          impact: density,
        } satisfies MapIncident,
      ];
    })
    .sort((a, b) => (b.impact ?? 0) - (a.impact ?? 0))
    .slice(0, 6);
}

function getFeatureMidpoint(feature: LineStringFeature): Coordinate | undefined {
  const coordinates = feature.geometry.coordinates;
  if (coordinates.length === 0) return undefined;

  return coordinates[Math.floor(coordinates.length / 2)];
}

function deriveAverageTripMinutes(trips: Trip[]): number | undefined {
  const durations = trips
    .map((trip) => trip.timestamps[trip.timestamps.length - 1] - trip.timestamps[0])
    .filter((duration) => Number.isFinite(duration) && duration > 0);

  if (durations.length === 0) return undefined;

  return Math.round((durations.reduce((total, duration) => total + duration, 0) / durations.length / 60) * 10) / 10;
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

function agentTripColor(type: AgentType): [number, number, number] {
  if (type === "truck") return [97, 186, 218];
  if (type === "bus") return [204, 137, 74];
  return [255, 200, 0];
}

function agentCssColor(type: AgentType): string {
  const [red, green, blue] = agentTripColor(type);
  return `rgb(${red}, ${green}, ${blue})`;
}

function agentTypeLabel(type: AgentType): string {
  if (type === "truck") return "Trucks";
  if (type === "bus") return "Buses";
  return "Cars";
}

function cycleTrafficLightColor(
  baseColor: TrafficLight["color"],
  currentTimeSeconds: number,
  index: number,
): TrafficLight["color"] {
  const sequence: TrafficLight["color"][] = ["green", "yellow", "red"];
  const baseIndex = Math.max(0, sequence.indexOf(baseColor));
  const phaseIndex = Math.floor(currentTimeSeconds / 12 + index) % sequence.length;

  return sequence[(baseIndex + phaseIndex) % sequence.length];
}

function cycleCrossingPhase(crossing: PedestrianCrossing, currentTimeSeconds: number, index: number): CrossingPhase {
  if (crossing.nextSwitchSeconds !== undefined && crossing.nextSwitchSeconds > 0) return crossing.phase;

  const cycleSeconds = Math.max(12, crossing.cycleSeconds);
  const phaseTime = (currentTimeSeconds + index * 7) % cycleSeconds;

  if (phaseTime < cycleSeconds * 0.38) return "walk";
  if (phaseTime < cycleSeconds * 0.58) return "clearance";
  return "stop";
}

function yieldZoneFillColor(density: number): [number, number, number, number] {
  const load = clamp01(density);
  return [235, Math.round(188 - load * 62), Math.round(82 - load * 32), Math.round(38 + load * 52)];
}

function yieldZoneLineColor(priority: IntersectionPhysics["priority"]): [number, number, number, number] {
  if (priority === "roundabout") return [155, 216, 205, 220];
  if (priority === "major") return [244, 191, 65, 225];
  return [235, 124, 58, 225];
}

function yieldCoreColor(priority: IntersectionPhysics["priority"]): [number, number, number, number] {
  if (priority === "roundabout") return [96, 196, 166, 245];
  if (priority === "major") return [244, 191, 65, 245];
  return [235, 124, 58, 245];
}

function crossingPhaseColor(phase: CrossingPhase, intensity: number): [number, number, number, number] {
  const alpha = Math.round(76 + clamp01(intensity) * 84);
  if (phase === "walk") return [207, 63, 50, alpha];
  if (phase === "clearance") return [244, 191, 65, alpha];
  return [96, 196, 166, alpha];
}

function level7ColumnColor(column: JamColumn, activeMode: CalendarMode): [number, number, number, number] {
  const intensity = clamp01(column.intensity);
  const modeLift = column.mode && column.mode !== activeMode ? 0.72 : 1;

  if (column.scenario === "variant") {
    return [Math.round(72 + intensity * 42), Math.round(170 + intensity * 52), Math.round(190 + intensity * 42), 172];
  }

  return [
    Math.round((218 + intensity * 28) * modeLift),
    Math.round((154 - intensity * 38) * modeLift),
    Math.round((70 - intensity * 22) * modeLift),
    184,
  ];
}

function calendarPointColor(mode: CalendarMode, intensity: number): [number, number, number, number] {
  const alpha = Math.round(70 + clamp01(intensity) * 96);
  if (mode === "night") return [122, 154, 205, alpha];
  if (mode === "weekend") return [96, 196, 166, alpha];
  return [244, 191, 65, alpha];
}

function crossingPhaseStrokeColor(phase: CrossingPhase): [number, number, number, number] {
  if (phase === "walk") return [245, 103, 87, 245];
  if (phase === "clearance") return [244, 191, 65, 245];
  return [155, 216, 205, 245];
}

function severityColor(severity: IncidentSeverity, alpha: number): [number, number, number, number] {
  if (severity === "critical") return [207, 63, 50, alpha];
  if (severity === "high") return [235, 124, 58, alpha];
  if (severity === "medium") return [244, 191, 65, alpha];
  return [96, 196, 166, alpha];
}

function closureZoneFillColor(severity: IncidentSeverity): [number, number, number, number] {
  const [red, green, blue] = severityColor(severity, 1);
  return [red, green, blue, 72];
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

function isMapIncident(item: unknown): item is MapIncident {
  if (!item || typeof item !== "object") return false;

  const candidate = item as Partial<MapIncident>;
  return typeof candidate.title === "string" && isCoordinate(candidate.coordinates);
}

function isClosureZone(item: unknown): item is ClosureZone {
  if (!item || typeof item !== "object") return false;

  const candidate = item as Partial<ClosureZone>;
  return typeof candidate.title === "string" && Array.isArray(candidate.polygon);
}

function isIntersectionPhysics(item: unknown): item is IntersectionPhysics {
  if (!item || typeof item !== "object") return false;

  const candidate = item as Partial<IntersectionPhysics>;
  return typeof candidate.title === "string" && isCoordinate(candidate.coordinates);
}

function isPedestrianCrossing(item: unknown): item is PedestrianCrossing {
  if (!item || typeof item !== "object") return false;

  const candidate = item as Partial<PedestrianCrossing>;
  return typeof candidate.title === "string" && isCoordinate(candidate.coordinates);
}

function isLevel7Point(item: unknown): item is Level7Point {
  if (!item || typeof item !== "object") return false;

  const candidate = item as Partial<Level7Point>;
  return typeof candidate.label === "string" && isCoordinate(candidate.coordinates);
}

function isJamColumn(item: unknown): item is JamColumn {
  if (!item || typeof item !== "object") return false;

  const candidate = item as Partial<JamColumn>;
  return typeof candidate.label === "string" && isCoordinate(candidate.coordinates);
}

function isCoordinate(point: unknown): point is Coordinate {
  return Array.isArray(point) && point.length === 2 && Number.isFinite(point[0]) && Number.isFinite(point[1]);
}

function getTripEndTime(trip: Trip): number {
  return trip.timestamps[trip.timestamps.length - 1] ?? 0;
}

function clampInteger(value: number, min: number, max: number): number {
  if (!Number.isFinite(value)) return min;

  return Math.min(Math.max(Math.round(value), min), max);
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

function getPrimaryRoadKey(properties: RoadProperties): string {
  return getRoadLookupKeys(properties)[0] ?? String(properties.name ?? "");
}

function normalizeRoadId(id: string | number): string {
  return String(id).trim();
}

function getRecord(value: unknown): Record<string, unknown> | undefined {
  return value && typeof value === "object" && !Array.isArray(value) ? (value as Record<string, unknown>) : undefined;
}

function firstArray(...values: unknown[]): unknown[] {
  for (const value of values) {
    if (Array.isArray(value)) return value;
  }

  return [];
}

function normalizeCoordinate(value: unknown): Coordinate | undefined {
  if (isCoordinate(value)) return value;

  const record = getRecord(value);
  const lng = Number(record?.lng ?? record?.lon ?? record?.longitude);
  const lat = Number(record?.lat ?? record?.latitude);

  return Number.isFinite(lng) && Number.isFinite(lat) ? [lng, lat] : undefined;
}

function normalizePolygon(value: unknown): Coordinate[] {
  const geometry = getRecord(value);
  const coordinates =
    geometry?.type === "Polygon" && Array.isArray(geometry.coordinates)
      ? Array.isArray(geometry.coordinates[0])
        ? geometry.coordinates[0]
        : []
      : value;

  if (!Array.isArray(coordinates)) return [];

  return coordinates.flatMap((point) => {
    const coordinate = normalizeCoordinate(point);
    return coordinate ? [coordinate] : [];
  });
}

function normalizeIncidentType(value: unknown): IncidentType {
  if (value === "construction" || value === "closure" || value === "event") return value;
  return "accident";
}

function normalizeAgentType(value: unknown): AgentType {
  const normalized = String(value ?? "").toLowerCase();

  if (normalized === "truck" || normalized === "lorry" || normalized === "freight") return "truck";
  if (normalized === "bus" || normalized === "public_transport" || normalized === "transit") return "bus";
  return "car";
}

function normalizeBrakeReason(value: unknown): TripBrakeEvent["reason"] {
  if (value === "pedestrian" || value === "signal") return value;
  return "yield";
}

function normalizeIntersectionPriority(value: unknown): IntersectionPhysics["priority"] {
  if (value === "uncontrolled_intersection") return "minor";
  if (value === "minor" || value === "roundabout") return value;
  return "major";
}

function normalizeCrossingPhase(value: unknown): CrossingPhase {
  const normalized = String(value ?? "").toLowerCase();

  if (normalized === "walk" || normalized === "pedestrian" || normalized === "red_for_cars") return "walk";
  if (normalized === "clearance" || normalized === "yellow" || normalized === "flashing") return "clearance";
  return "stop";
}

function statusToCongestion(value: unknown): number | undefined {
  if (value === "congested") return 88;
  if (value === "heavy") return 66;
  if (value === "normal") return 34;
  return undefined;
}

function normalizeSeverity(value: unknown): IncidentSeverity {
  if (value === "critical" || value === "high" || value === "medium" || value === "low") return value;

  const numeric = Number(value);
  if (Number.isFinite(numeric)) {
    if (numeric >= 0.8 || numeric >= 80) return "critical";
    if (numeric >= 0.6 || numeric >= 60) return "high";
    if (numeric >= 0.35 || numeric >= 35) return "medium";
  }

  return "low";
}

function severityToImpact(severity: IncidentSeverity): number {
  if (severity === "critical") return 0.9;
  if (severity === "high") return 0.7;
  if (severity === "medium") return 0.48;
  return 0.25;
}

function incidentTypeLabel(type: IncidentType): string {
  if (type === "construction") return "Road works";
  if (type === "closure") return "Road closure";
  if (type === "event") return "Public event";
  return "Traffic accident";
}

function intersectionPriorityLabel(priority: IntersectionPhysics["priority"]): string {
  if (priority === "minor") return "minor road yields";
  if (priority === "roundabout") return "roundabout priority";
  return "major road priority";
}

function crossingPhaseLabel(phase: CrossingPhase): string {
  if (phase === "walk") return "pedestrian walk phase";
  if (phase === "clearance") return "clearance phase";
  return "vehicle flow phase";
}

function optionalNumber(value: unknown): number | undefined {
  const number = Number(value);
  return Number.isFinite(number) ? number : undefined;
}

function optionalInteger(value: unknown): number | undefined {
  const number = optionalNumber(value);
  return number === undefined ? undefined : Math.round(number);
}

function optionalString(value: unknown): string | undefined {
  return typeof value === "string" && value.trim().length > 0 ? value : undefined;
}

function optionalImpact(value: unknown): number | undefined {
  const number = optionalNumber(value);
  return number === undefined ? undefined : normalizeRatio(number);
}

function normalizePercent(value: unknown): number {
  const number = Number(value);
  if (!Number.isFinite(number)) return 0;

  return clampPercent(number <= 1 ? number * 100 : number);
}

function normalizeRatio(value: number): number {
  return clamp01(value > 1 ? value / 100 : value);
}

function clamp01(value: number): number {
  if (!Number.isFinite(value)) return 0;
  return Math.min(Math.max(value, 0), 1);
}

function clampPercent(value: number): number {
  if (!Number.isFinite(value)) return 0;
  return Math.min(Math.max(value, 0), 100);
}

function coordinateSeed(coordinates: Coordinate): number {
  const raw = Math.sin(coordinates[0] * 12_989.8 + coordinates[1] * 78_233) * 43_758.5453;
  return raw - Math.floor(raw);
}

function hasAnalyticsData(analytics: Level4Analytics): boolean {
  return (
    analytics.metrics.congestionIndex > 0 ||
    analytics.incidents.length > 0 ||
    analytics.closureZones.length > 0 ||
    analytics.timeSeries.length > 0 ||
    analytics.forecast.length > 0 ||
    analytics.bottlenecks.length > 0
  );
}

function hasPhysicsData(physics: Level6Physics): boolean {
  return (
    physics.agentProfiles.length > 0 ||
    physics.intersections.length > 0 ||
    physics.pedestrianCrossings.length > 0
  );
}

function hasLevel7Data(level7: Level7Patterns): boolean {
  return (
    level7.calendarPatterns.length > 0 ||
    level7.attractionPoints.length > 0 ||
    level7.jamColumns.length > 0 ||
    level7.comparisons.length > 0
  );
}

function offsetCoordinate(coordinates: Coordinate, eastMeters: number, northMeters: number): Coordinate {
  const metersPerDegreeLat = 111_320;
  const metersPerDegreeLng = metersPerDegreeLat * Math.cos((coordinates[1] / 180) * Math.PI);

  return [coordinates[0] + eastMeters / metersPerDegreeLng, coordinates[1] + northMeters / metersPerDegreeLat];
}

function normalizeSignedPercent(value: number): number {
  if (!Number.isFinite(value)) return 0;

  const percent = Math.abs(value) <= 1 ? value * 100 : value;
  return Math.min(Math.max(percent, -100), 100);
}

function calendarAttractorLabel(mode: CalendarMode, index: number): string {
  if (mode === "night") return index % 2 === 0 ? "Night logistics pocket" : "Late service cluster";
  if (mode === "weekend") return index % 2 === 0 ? "Weekend leisure pull" : "Retail demand shift";
  return index % 2 === 0 ? "Morning commuter pull" : "Office corridor demand";
}

function calendarModeLabel(mode: CalendarMode): string {
  if (mode === "weekend") return "Weekend";
  if (mode === "night") return "Night";
  return "Weekday";
}

function calendarModeToApiPattern(mode: CalendarMode): string {
  if (mode === "weekend") return "weekend";
  if (mode === "night") return "night";
  return "normal";
}

function formatPercent(value: number): string {
  return `${Math.round(normalizeRatio(value) * 100)}%`;
}

function formatSignedPercent(value: number): string {
  const normalized = normalizeSignedPercent(value);
  const sign = normalized > 0 ? "+" : "";

  return `${sign}${Math.round(normalized)}%`;
}

function formatTimeOfDay(seconds: number): string {
  const safeSeconds = clampInteger(seconds, 0, DAY_SECONDS - 1);
  const hours = Math.floor(safeSeconds / 3600);
  const minutes = Math.floor((safeSeconds % 3600) / 60);

  return `${String(hours).padStart(2, "0")}:${String(minutes).padStart(2, "0")}`;
}

function formatMinutes(value: number | undefined): string {
  return value === undefined ? "n/a" : `${value.toFixed(value >= 10 ? 0 : 1)}m`;
}

function formatThroughput(value: number | undefined): string {
  return value === undefined ? "n/a" : `${Math.round(value).toLocaleString("en-US")}/h`;
}

function escapeCsvCell(value: string): string {
  if (!/[",\n]/.test(value)) return value;
  return `"${value.replaceAll('"', '""')}"`;
}
