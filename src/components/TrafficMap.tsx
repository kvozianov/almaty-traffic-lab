"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import DeckGL from "@deck.gl/react";
import { GeoJsonLayer, IconLayer, PolygonLayer, ScatterplotLayer } from "@deck.gl/layers";
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

type Coordinate = [number, number];
type IncidentSeverity = "low" | "medium" | "high" | "critical";
type IncidentType = "accident" | "construction" | "closure" | "event";

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

type MapSelection =
  | { kind: "road"; title: string; detail: string }
  | { kind: "incident"; title: string; detail: string }
  | { kind: "closure"; title: string; detail: string }
  | { kind: "light"; title: string; detail: string };

type TrafficMapProps = {
  className?: string;
  mapStyle?: string;
  roadsEndpoint?: string;
  trafficEndpoint?: string;
  tripsEndpoint?: string;
  analyticsEndpoint?: string;
  analyticsExportEndpoint?: string;
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

export default function TrafficMap({
  className,
  mapStyle = CARTO_DARK_MATTER_STYLE,
  roadsEndpoint = "/api/roads",
  trafficEndpoint = "/api/traffic",
  tripsEndpoint = "/api/trips",
  analyticsEndpoint = "/api/analytics",
  analyticsExportEndpoint = "/api/analytics/export",
}: TrafficMapProps) {
  const [roads, setRoads] = useState<RoadFeatureCollection>({ type: "FeatureCollection", features: [] });
  const [traffic, setTraffic] = useState<TrafficPayload>({ lights: [], roads: [] });
  const [trips, setTrips] = useState<Trip[]>([]);
  const [analytics, setAnalytics] = useState<Level4Analytics>(EMPTY_ANALYTICS);
  const [currentTime, setCurrentTime] = useState(0);
  const [isPlaying, setIsPlaying] = useState(true);
  const [simulationSpeed, setSimulationSpeed] = useState(DEFAULT_TRIP_ANIMATION_SPEED);
  const [trafficDensity, setTrafficDensity] = useState(DEFAULT_TRAFFIC_DENSITY);
  const [requestedTrafficDensity, setRequestedTrafficDensity] = useState(DEFAULT_TRAFFIC_DENSITY);
  const [tripsLayerOpacity, setTripsLayerOpacity] = useState(TRIPS_LAYER_TARGET_OPACITY);
  const [loadState, setLoadState] = useState<LoadState>("idle");
  const [trafficState, setTrafficState] = useState<LoadState>("idle");
  const [tripsState, setTripsState] = useState<LoadState>("idle");
  const [analyticsState, setAnalyticsState] = useState<LoadState>("idle");
  const [error, setError] = useState<string | null>(null);
  const [trafficError, setTrafficError] = useState<string | null>(null);
  const [tripsError, setTripsError] = useState<string | null>(null);
  const [analyticsError, setAnalyticsError] = useState<string | null>(null);
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
        const response = await fetch(buildTripsRequestUrl(tripsEndpoint, requestedTrafficDensity), {
          headers: { Accept: "application/json" },
          signal: controller.signal,
        });

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
  }, [animateTripsOpacity, requestedTrafficDensity, tripsEndpoint]);

  useEffect(() => {
    const controller = new AbortController();

    async function loadAnalytics() {
      setAnalyticsState("loading");
      setAnalyticsError(null);

      try {
        const response = await fetch(analyticsEndpoint, {
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
  }, [analyticsEndpoint]);

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

  const updateHoveredRoad = useCallback((properties: RoadProperties | null) => {
    setHoveredRoad((current) => {
      const currentKey = current ? getPrimaryRoadKey(current) : null;
      const nextKey = properties ? getPrimaryRoadKey(properties) : null;

      return currentKey === nextKey ? current : properties;
    });
  }, []);

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
    [roadsWithTraffic, updateHoveredRoad],
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
    [traffic.lights],
  );

  const closureZoneLayer = useMemo(
    () =>
      new PolygonLayer<ClosureZone>({
        id: "level4-closure-zones",
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
    [snapshot.closureZones],
  );

  const incidentLayer = useMemo(
    () =>
      new IconLayer<MapIncident>({
        id: "level4-incidents",
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
    [snapshot.incidents],
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

  const tripsLayer = useMemo(
    () =>
      new TripsLayer<Trip>({
        id: "agent-vehicle-trips",
        data: trips,
        getPath: (trip) => trip.path,
        getTimestamps: (trip) => trip.timestamps,
        getColor: [255, 200, 0],
        getWidth: 5,
        opacity: tripsLayerOpacity,
        widthMinPixels: 2.5,
        widthMaxPixels: 10,
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
    [currentTime, trips, tripsLayerOpacity],
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
    return `${roads.features.length.toLocaleString("en-US")} road segments | ${traffic.lights.length.toLocaleString(
      "en-US",
    )} lights | ${traffic.roads.length.toLocaleString("en-US")} density updates | ${trips.length.toLocaleString(
      "en-US",
    )} trips | ${analyticsState === "ready" ? "level 4 analytics online" : "waiting for level 4 analytics API"}`;
  }, [
    analyticsError,
    analyticsState,
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

  return (
    <section className={[styles.shell, className].filter(Boolean).join(" ")} aria-label="Almaty traffic map">
      <DeckGL
        initialViewState={ALMATY_VIEW_STATE}
        controller
        layers={[roadLayer, tripsLayer, trafficLightLayer, closureZoneLayer, incidentLayer]}
        getTooltip={({ object }) => buildTooltip(object)}
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
        <h1 className={styles.title}>Level 4 command view</h1>
        <p className={styles.meta}>Almaty center | live vehicles, roads, incidents, closures</p>
        {hoveredRoad ? (
          <p className={styles.meta}>
            {String(hoveredRoad.name || hoveredRoad.id || hoveredRoad.osmid || "Road")} | density{" "}
            {Number(hoveredRoad.density ?? hoveredRoad.load ?? 0).toFixed(2)}
          </p>
        ) : null}
      </div>

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
        className={[styles.status, loadState === "error" || analyticsState === "error" ? styles.statusError : ""]
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

function buildTripsRequestUrl(endpoint: string, count: number): string {
  const requestUrl = new URL(endpoint, window.location.origin);

  requestUrl.searchParams.set("count", String(clampInteger(count, MIN_TRAFFIC_DENSITY, MAX_TRAFFIC_DENSITY)));

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

  return {
    path,
    timestamps,
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
    incidents: analytics.incidents,
    closureZones: analytics.closureZones,
    timeSeries,
    forecast: analytics.forecast,
    bottlenecks:
      analytics.bottlenecks.length > 0 ? analytics.bottlenecks : deriveBottlenecks(roadsWithTraffic.features),
  };
}

function buildTooltip(object: unknown) {
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

function formatPercent(value: number): string {
  return `${Math.round(normalizeRatio(value) * 100)}%`;
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
