"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { Map as MapLibre, Marker, type MapRef } from "@vis.gl/react-maplibre";
import type { FeatureCollection, LineString } from "geojson";
import { setWorkerUrl, type GeoJSONSource, type Map as MaplibreMap, type MapMouseEvent } from "maplibre-gl";
import type { CityData } from "@/lab/client/data";
import type { Change } from "@/lab/engine/types";
import { DIFF_MIN_SHARE, DIFF_MIN_VEHICLES, diffColor, loadColor, type RGBA } from "./colors";
import FlowParticles, { TONES } from "./FlowParticles";
import styles from "./LabMap.module.css";

const MAP_STYLE = "https://tiles.openfreemap.org/styles/positron";

// See scripts/copy-maplibre-worker.mjs.
if (typeof window !== "undefined") setWorkerUrl("/vendor/maplibre/maplibre-gl-worker.mjs");
export const ALMATY_VIEW = { longitude: 76.915, latitude: 43.245, zoom: 11.2 };
const INK = "#141413";

/** `time` is congested travel time per edge (minutes), used by the traffic animation. */
export type MapColoring =
  | { kind: "load"; flow: ArrayLike<number>; vc: ArrayLike<number>; time: ArrayLike<number> }
  | { kind: "diff"; before: ArrayLike<number>; after: ArrayLike<number>; time: ArrayLike<number> };

/** A pill on the map naming a street whose traffic changed. */
export interface StreetLabel {
  street: number;
  name: string;
  pct: number;
  lon: number;
  lat: number;
}

const prefersReducedMotion = () =>
  typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

export interface LabMapProps {
  data: CityData;
  coloring: MapColoring;
  selectedSection?: number | null;
  changes?: Change[];
  placing?: boolean;
  interactive?: boolean;
  /** Fit the map to this bbox when it changes. */
  focus?: [number, number, number, number] | null;
  /** A building location chosen but not yet added to the scenario. */
  pendingPoint?: { lon: number; lat: number } | null;
  /** Street to emphasise: drawn with a dark outline while other roads fade. */
  highlightStreet?: number | null;
  streetLabels?: StreetLabel[];
  onPickStreet?: (street: number) => void;
  onHoverStreet?: (street: number | null) => void;
  onPickSection?: (section: number) => void;
  onPickPoint?: (lon: number, lat: number) => void;
  onClear?: () => void;
}

function widthFor(flow: number): number {
  return 0.9 + 3.6 * Math.sqrt(Math.min(flow, 9000) / 9000);
}

const rgba = (c: RGBA) => `rgba(${c[0]},${c[1]},${c[2]},${(c[3] / 255).toFixed(3)})`;

/** Width scaled up when zooming into a neighbourhood. */
const zoomed = (expr: unknown) => [
  "interpolate",
  ["linear"],
  ["zoom"],
  10,
  ["*", 0.8, expr],
  14,
  ["*", 1.6, expr],
  17,
  ["*", 3, expr],
];

/** Directed edges as GeoJSON; feature id = edge index, so feature-state can recolour them. */
function roadsGeoJson(data: CityData): FeatureCollection<LineString> {
  return {
    type: "FeatureCollection",
    features: data.paths.map((coordinates, e) => ({
      type: "Feature",
      id: e,
      properties: { section: data.graph.edges.section[e], street: data.graph.edges.street[e] },
      geometry: { type: "LineString", coordinates },
    })),
  };
}

/** The basemap's first label layer: our roads go below it so street names stay readable. */
function firstSymbolLayer(map: MaplibreMap): string | undefined {
  return map.getStyle().layers?.find((l) => l.type === "symbol")?.id;
}

export default function LabMap({
  data,
  coloring,
  selectedSection = null,
  changes = [],
  placing = false,
  interactive = true,
  focus = null,
  pendingPoint = null,
  highlightStreet = null,
  streetLabels = [],
  onPickStreet,
  onHoverStreet,
  onPickSection,
  onPickPoint,
  onClear,
}: LabMapProps) {
  const mapRef = useRef<MapRef>(null);
  const [ready, setReady] = useState(false);
  const [hoverSection, setHoverSection] = useState<number | null>(null);
  const [mapInstance, setMapInstance] = useState<MaplibreMap | null>(null);
  const [animate, setAnimate] = useState(() => !prefersReducedMotion());
  const edgeCount = data.graph.edges.from.length;

  // Latest callbacks for the imperative map listeners.
  const handlers = useRef({ onPickSection, onPickPoint, onClear, placing, interactive });
  useEffect(() => {
    handlers.current = { onPickSection, onPickPoint, onClear, placing, interactive };
  });

  const style = useMemo(() => {
    const colors: string[] = new Array(edgeCount);
    const widths = new Float32Array(edgeCount);
    for (let e = 0; e < edgeCount; e++) {
      if (coloring.kind === "load") {
        colors[e] = rgba(loadColor(coloring.vc[e]));
        widths[e] = widthFor(coloring.flow[e]);
      } else {
        colors[e] = rgba(diffColor(coloring.before[e], coloring.after[e]));
        widths[e] = widthFor(Math.max(coloring.before[e], coloring.after[e]));
      }
    }
    return { colors, widths };
  }, [coloring, edgeCount]);

  const { closedSections, changedSections } = useMemo(() => {
    const closed: number[] = [];
    const other: number[] = [];
    for (const c of changes) {
      if (c.type === "development") continue;
      (c.type === "close" ? closed : other).push(c.section);
    }
    return { closedSections: closed, changedSections: other };
  }, [changes]);

  const developments = useMemo(
    () => changes.filter((c): c is Extract<Change, { type: "development" }> => c.type === "development"),
    [changes],
  );

  /* ---------------------------------------------------------- setup */
  const onLoad = () => {
    const map = mapRef.current?.getMap();
    if (!map) return;
    const before = firstSymbolLayer(map);
    map.addSource("roads", { type: "geojson", data: roadsGeoJson(data) });
    map.addSource("developments", { type: "geojson", data: { type: "FeatureCollection", features: [] } });
    const width = zoomed(["coalesce", ["feature-state", "w"], 1]);
    const haloWidth = zoomed(["+", ["coalesce", ["feature-state", "w"], 1], 3]);
    const offset = ["interpolate", ["linear"], ["zoom"], 10, 0.8, 14, 2.4, 17, 5];
    const none = ["==", ["get", "section"], -2];
    const round = { "line-cap": "round", "line-join": "round" } as const;
    map.addLayer(
      {
        id: "roads-halo",
        type: "line",
        source: "roads",
        filter: none as never,
        layout: round,
        paint: { "line-color": INK, "line-width": haloWidth as never, "line-offset": offset as never },
      },
      before,
    );
    map.addLayer(
      {
        id: "roads-street",
        type: "line",
        source: "roads",
        filter: none as never,
        layout: round,
        paint: { "line-color": INK, "line-width": haloWidth as never, "line-offset": offset as never },
      },
      before,
    );
    map.addLayer(
      {
        id: "roads",
        type: "line",
        source: "roads",
        layout: round,
        paint: {
          "line-color": ["coalesce", ["feature-state", "c"], "#d9d6cd"] as never,
          "line-width": width as never,
          "line-offset": offset as never,
        },
      },
      before,
    );
    map.addLayer(
      {
        id: "roads-hover",
        type: "line",
        source: "roads",
        filter: none as never,
        layout: round,
        paint: { "line-color": INK, "line-width": width as never, "line-offset": offset as never },
      },
      before,
    );
    map.addLayer(
      {
        id: "roads-closed",
        type: "line",
        source: "roads",
        filter: none as never,
        paint: { "line-color": INK, "line-width": 2.5, "line-dasharray": [2, 1.5] },
      },
      before,
    );
    map.addLayer({
      id: "developments",
      type: "circle",
      source: "developments",
      paint: {
        "circle-radius": 8,
        "circle-color": INK,
        "circle-stroke-color": "#ffffff",
        "circle-stroke-width": 2.5,
      },
    });

    const pickSection = (e: MapMouseEvent): number => {
      const pad = 5;
      const features = map.queryRenderedFeatures(
        [
          [e.point.x - pad, e.point.y - pad],
          [e.point.x + pad, e.point.y + pad],
        ],
        { layers: ["roads"] },
      );
      for (const f of features) {
        const s = Number(f.properties?.section);
        if (s >= 0) return s;
      }
      return -1;
    };
    map.on("mousemove", (e) => {
      const h = handlers.current;
      if (!h.interactive) return;
      if (h.placing) {
        map.getCanvas().style.cursor = "crosshair";
        setHoverSection(null);
        return;
      }
      const s = pickSection(e);
      map.getCanvas().style.cursor = s >= 0 ? "pointer" : "";
      setHoverSection(s >= 0 ? s : null);
    });
    map.on("mouseout", () => setHoverSection(null));
    map.on("click", (e) => {
      const h = handlers.current;
      if (!h.interactive) return;
      if (h.placing) {
        h.onPickPoint?.(e.lngLat.lng, e.lngLat.lat);
        return;
      }
      const s = pickSection(e);
      if (s >= 0) h.onPickSection?.(s);
      else h.onClear?.();
    });
    setMapInstance(map);
    setReady(true);
  };

  /* ---------------------------------------------------------- updates */
  useEffect(() => {
    const map = mapRef.current?.getMap();
    if (!ready || !map) return;
    for (let e = 0; e < edgeCount; e++) {
      map.setFeatureState({ source: "roads", id: e }, { c: style.colors[e], w: style.widths[e] });
    }
  }, [ready, style, edgeCount]);

  useEffect(() => {
    const map = mapRef.current?.getMap();
    if (!ready || !map) return;
    const inSections = (ids: number[]) => ["in", ["get", "section"], ["literal", ids]];
    const halo = [...changedSections, ...(selectedSection !== null ? [selectedSection] : [])];
    map.setFilter("roads-halo", inSections(halo) as never);
    map.setPaintProperty("roads-halo", "line-opacity", selectedSection !== null ? 1 : 0.45);
    map.setFilter("roads-closed", inSections(closedSections) as never);
    map.setFilter("roads", ["!", inSections(closedSections)] as never);
    map.setFilter("roads-hover", inSections(hoverSection !== null && !placing ? [hoverSection] : []) as never);
    (map.getSource("developments") as GeoJSONSource).setData({
      type: "FeatureCollection",
      features: [...developments, ...(pendingPoint ? [pendingPoint] : [])].map((d) => ({
        type: "Feature",
        properties: {},
        geometry: { type: "Point", coordinates: [d.lon, d.lat] },
      })),
    });
  }, [ready, selectedSection, changedSections, closedSections, hoverSection, placing, developments, pendingPoint]);

  useEffect(() => {
    const map = mapRef.current?.getMap();
    if (!ready || !map) return;
    const on = highlightStreet !== null;
    map.setFilter("roads-street", ["==", ["get", "street"], on ? highlightStreet : -2] as never);
    map.setPaintProperty(
      "roads",
      "line-opacity",
      (on ? ["case", ["==", ["get", "street"], highlightStreet], 1, 0.28] : 1) as never,
    );
  }, [ready, highlightStreet]);

  // Particle colour follows the map: dark "cars" on the load map; red/blue where traffic grew/shrank.
  const tones = useMemo(() => {
    const out = new Uint8Array(edgeCount).fill(TONES.indexOf("ink"));
    if (coloring.kind === "diff") {
      for (let e = 0; e < edgeCount; e++) {
        const d = coloring.after[e] - coloring.before[e];
        const noise = Math.abs(d) < DIFF_MIN_VEHICLES || Math.abs(d) / Math.max(coloring.before[e], 100) < DIFF_MIN_SHARE;
        out[e] = TONES.indexOf(noise ? "same" : d > 0 ? "more" : "less");
      }
    }
    return out;
  }, [coloring, edgeCount]);

  useEffect(() => {
    if (!focus || !mapRef.current) return;
    const [x0, y0, x1, y1] = focus;
    mapRef.current.fitBounds(
      [
        [x0, y0],
        [x1, y1],
      ],
      { padding: window.innerWidth < 900 ? 32 : 120, maxZoom: 15, duration: 700 },
    );
  }, [focus]);

  return (
    <div className={`${styles.map} ${placing ? styles.placing : ""}`}>
      <MapLibre
        ref={mapRef}
        initialViewState={ALMATY_VIEW}
        mapStyle={MAP_STYLE}
        onLoad={onLoad}
        interactive={interactive}
        dragRotate={false}
        pitchWithRotate={false}
        touchPitch={false}
        minZoom={9.5}
        maxZoom={17}
        attributionControl={{ compact: true }}
        style={{ width: "100%", height: "100%" }}
      >
        {streetLabels.map((l) => (
          <Marker key={l.street} longitude={l.lon} latitude={l.lat} anchor="bottom">
            <button
              type="button"
              className={`${styles.streetPill} ${highlightStreet === l.street ? styles.streetPillActive : ""}`}
              onClick={(ev) => {
                ev.stopPropagation();
                onPickStreet?.(l.street);
              }}
              onMouseEnter={() => onHoverStreet?.(l.street)}
              onMouseLeave={() => onHoverStreet?.(null)}
            >
              <span>{l.name.replace(/ (Street|Avenue|Boulevard|Highway)$/, "")}</span>
              <span className={l.pct > 0 ? styles.pillMore : styles.pillLess}>
                {l.pct > 0 ? "▲" : "▼"} {Math.abs(l.pct).toFixed(0)}%
              </span>
            </button>
          </Marker>
        ))}
      </MapLibre>
      <FlowParticles
        map={mapInstance}
        data={data}
        flow={coloring.kind === "load" ? coloring.flow : coloring.after}
        time={coloring.time}
        tones={tones}
        focusStreet={highlightStreet}
        enabled={animate && ready}
      />
      {ready && (
        <button
          type="button"
          className={styles.animateToggle}
          aria-pressed={animate}
          onClick={() => setAnimate((a) => !a)}
        >
          <span className={styles.animateDot} aria-hidden="true" />
          {animate ? "Traffic moving" : "Show moving traffic"}
        </button>
      )}
      {!ready && (
        <p className={`label ${styles.loading}`} role="status">
          Loading map…
        </p>
      )}
    </div>
  );
}
