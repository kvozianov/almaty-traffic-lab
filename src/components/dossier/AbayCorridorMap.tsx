"use client";

import { useEffect, useMemo, useState } from "react";
import DeckGL from "@deck.gl/react";
import { GeoJsonLayer, LineLayer } from "@deck.gl/layers";
import { Map as MapLibre } from "@vis.gl/react-maplibre";
import type { StyleSpecification } from "maplibre-gl";
import styles from "./AbayCorridorMap.module.css";

const ALMATY_DARK_CONTEXT_STYLE: StyleSpecification = {
  version: 8,
  sources: {},
  layers: [
    {
      id: "almaty-dossier-background",
      type: "background",
      paint: {
        "background-color": "#10110f",
      },
    },
  ],
};

type Coordinate = [number, number];

type RoadProperties = {
  id?: string;
  osmid?: string | number;
  name?: string;
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

type CorridorSegment = {
  id: string;
  source: Coordinate;
  target: Coordinate;
};

const ALMATY_ABAY_VIEW_STATE = {
  longitude: 76.936,
  latitude: 43.2412,
  zoom: 12.8,
  pitch: 0,
  bearing: -83,
};

const ABAY_FOCUS_BOUNDS = {
  minLng: 76.912,
  maxLng: 76.958,
  minLat: 43.236,
  maxLat: 43.247,
};

function isCoordinateInFocus([longitude, latitude]: Coordinate) {
  return (
    longitude >= ABAY_FOCUS_BOUNDS.minLng &&
    longitude <= ABAY_FOCUS_BOUNDS.maxLng &&
    latitude >= ABAY_FOCUS_BOUNDS.minLat &&
    latitude <= ABAY_FOCUS_BOUNDS.maxLat
  );
}

function isAbayFeature(feature: LineStringFeature) {
  const name = String(feature.properties?.name ?? "").toLowerCase();
  return name.includes("абай") && feature.geometry.coordinates.some(isCoordinateInFocus);
}

function toSegments(features: LineStringFeature[]): CorridorSegment[] {
  return features.flatMap((feature, featureIndex) => {
    const points = feature.geometry.coordinates.filter(isCoordinateInFocus);
    const segments: CorridorSegment[] = [];

    for (let index = 1; index < points.length; index += 1) {
      segments.push({
        id: `${feature.properties?.id ?? feature.properties?.osmid ?? featureIndex}-${index}`,
        source: points[index - 1],
        target: points[index],
      });
    }

    return segments;
  });
}

export default function AbayCorridorMap({
  evidence,
  runId,
  expectedSourceSha256,
}: {
  evidence: {
    available: boolean;
    claimLevel: string;
    freshness?: string;
  };
  runId: string;
  expectedSourceSha256: string;
}) {
  const [roads, setRoads] = useState<RoadFeatureCollection | null>(null);
  const [loadState, setLoadState] = useState<"loading" | "ready" | "unavailable">("loading");

  useEffect(() => {
    const controller = new AbortController();

    fetch(`/api/roads?runId=${encodeURIComponent(runId)}`, { signal: controller.signal })
      .then((response) => {
        if (!response.ok) throw new Error(`Road fetch failed: ${response.status}`);
        if (
          response.headers.get("x-portfolio-run-id") !== runId ||
          response.headers.get("x-portfolio-source-sha256") !== expectedSourceSha256
        ) {
          throw new Error("Road evidence belongs to another immutable release.");
        }
        return response.json() as Promise<RoadFeatureCollection>;
      })
      .then((payload) => {
        if (payload?.type === "FeatureCollection" && Array.isArray(payload.features)) {
          setRoads(payload);
          setLoadState("ready");
        } else {
          setLoadState("unavailable");
        }
      })
      .catch(() => {
        if (!controller.signal.aborted) {
          setLoadState("unavailable");
        }
      });

    return () => controller.abort();
  }, [expectedSourceSha256, runId]);

  const corridorFeatures = useMemo(() => roads?.features.filter(isAbayFeature) ?? [], [roads]);
  const corridorSegments = useMemo(() => toSegments(corridorFeatures), [corridorFeatures]);

  const layers = useMemo(
    () => [
      new GeoJsonLayer<LineStringFeature>({
        id: "almaty-muted-roads",
        data: roads ?? { type: "FeatureCollection", features: [] },
        stroked: true,
        filled: false,
        getLineColor: [76, 76, 72, 66],
        getLineWidth: 1,
        lineWidthMinPixels: 0.6,
        lineWidthMaxPixels: 1.4,
        pickable: false,
      }),
      new LineLayer<CorridorSegment>({
        id: "abay-corridor-highlight",
        data: corridorSegments,
        getSourcePosition: (segment) => segment.source,
        getTargetPosition: (segment) => segment.target,
        getColor: [219, 133, 45, 255],
        getWidth: 7,
        widthUnits: "pixels",
        pickable: false,
      }),
    ],
    [corridorSegments, roads],
  );

  return (
    <div
      data-testid="abay-corridor-map"
      data-portfolio-run-id={runId}
      data-source-sha256={expectedSourceSha256}
      className={`${styles.shell} relative h-full min-h-[320px] overflow-hidden bg-[#11110f] sm:min-h-[420px]`}
    >
      <DeckGL
        initialViewState={ALMATY_ABAY_VIEW_STATE}
        controller={{ dragRotate: false }}
        layers={layers}
        widgets={[]}
        style={{ position: "relative", width: "100%", height: "100%" }}
      >
        <MapLibre mapStyle={ALMATY_DARK_CONTEXT_STYLE} attributionControl={false} reuseMaps style={{ width: "100%", height: "100%" }} />
      </DeckGL>

      <div
        data-testid="map-evidence-status"
        className="absolute bottom-4 left-4 right-4 flex flex-wrap items-center justify-between gap-2 rounded-[6px] border border-white/10 bg-[#151512]/90 px-2.5 py-1.5 text-[11px] font-medium text-white/78 backdrop-blur"
        role="status"
        aria-live="polite"
      >
        <span title={evidence.freshness}>
          {loadState === "loading"
            ? "Геометрия дорог загружается"
            : loadState === "unavailable"
              ? "Геометрия дорог недоступна"
              : evidence.available
                ? `Снимок дорог · ${evidence.claimLevel}`
                : "Геометрия загружена · доказательство источника отсутствует"}
        </span>
        <a
          href="https://www.openstreetmap.org/copyright"
          target="_blank"
          rel="noreferrer"
          className="rounded-sm text-white/80 underline decoration-white/35 underline-offset-2 hover:text-white focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white"
        >
          © OpenStreetMap contributors
        </a>
      </div>
    </div>
  );
}
