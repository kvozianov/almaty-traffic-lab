"use client";

import { useEffect, useMemo, useRef } from "react";
import type { Map as MaplibreMap } from "maplibre-gl";
import type { CityData } from "@/lab/client/data";
import styles from "./LabMap.module.css";

/**
 * Animated traffic: dots travel along every road link. Their number follows
 * the modelled flow (vehicle-km) and their speed the congested travel time,
 * so free-flowing roads stream and jammed ones crawl. One animation second is
 * SIM_MINUTES_PER_SECOND minutes of real time.
 */
const SIM_MINUTES_PER_SECOND = 1.5;
const M_PER_DEG_LON = 81_095.6;
const M_PER_DEG_LAT = 111_132.0;

export type ParticleTone = "ink" | "more" | "less" | "same";

// Light "headlights" read well on top of the coloured road lines; roads whose
// traffic did not change keep fainter dots so the eye goes to the changes.
const TONE_COLORS: Record<ParticleTone, string> = {
  ink: "rgba(255, 255, 255, 0.95)",
  more: "rgba(255, 255, 255, 0.98)",
  less: "rgba(255, 255, 255, 0.98)",
  same: "rgba(255, 255, 255, 0.55)",
};
export const TONES = Object.keys(TONE_COLORS) as ParticleTone[];

/** Small seeded PRNG (mulberry32): the same map always gets the same particles. */
function seeded(seed: number) {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

interface Geometry {
  /** Edge e's points are pts[start[e] .. start[e + 1]). */
  start: Int32Array;
  lon: Float64Array;
  lat: Float64Array;
  /** Cumulative metres from the edge start to each point. */
  cum: Float64Array;
  /** Screen-space unit normal (right of travel) of the segment starting at each point. */
  nx: Float32Array;
  ny: Float32Array;
  length: Float64Array;
}

function buildGeometry(data: CityData): Geometry {
  const paths = data.paths;
  const start = new Int32Array(paths.length + 1);
  let total = 0;
  for (let e = 0; e < paths.length; e++) {
    start[e] = total;
    total += paths[e].length;
  }
  start[paths.length] = total;
  const lon = new Float64Array(total);
  const lat = new Float64Array(total);
  const cum = new Float64Array(total);
  const nx = new Float32Array(total);
  const ny = new Float32Array(total);
  const length = new Float64Array(paths.length);
  for (let e = 0; e < paths.length; e++) {
    const p = paths[e];
    let acc = 0;
    for (let k = 0; k < p.length; k++) {
      const i = start[e] + k;
      lon[i] = p[k][0];
      lat[i] = p[k][1];
      if (k > 0) {
        const dx = (p[k][0] - p[k - 1][0]) * M_PER_DEG_LON;
        const dy = (p[k][1] - p[k - 1][1]) * M_PER_DEG_LAT;
        acc += Math.sqrt(dx * dx + dy * dy);
      }
      cum[i] = acc;
      if (k + 1 < p.length) {
        // Screen y grows downwards, so travel direction is (dx, -dy); right-hand normal is (dy, dx).
        const dx = (p[k + 1][0] - p[k][0]) * M_PER_DEG_LON;
        const dy = (p[k + 1][1] - p[k][1]) * M_PER_DEG_LAT;
        const n = Math.sqrt(dx * dx + dy * dy) || 1;
        nx[i] = dy / n;
        ny[i] = dx / n;
      }
    }
    length[e] = acc;
  }
  return { start, lon, lat, cum, nx, ny, length };
}

export interface FlowParticlesProps {
  map: MaplibreMap | null;
  data: CityData;
  flow: ArrayLike<number>;
  /** Congested travel time per edge, minutes. */
  time: ArrayLike<number>;
  /** Per edge: index into TONES. */
  tones: Uint8Array;
  /** When set, particles on other streets are dimmed. */
  focusStreet?: number | null;
  enabled: boolean;
}

export default function FlowParticles({ map, data, flow, time, tones, focusStreet = null, enabled }: FlowParticlesProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  // Read inside the animation loop, so changing focus does not restart it.
  const focusRef = useRef<number | null>(focusStreet);
  useEffect(() => {
    focusRef.current = focusStreet;
  }, [focusStreet]);
  const geometry = useMemo(() => buildGeometry(data), [data]);

  // Particles: edge, distance along it (m), speed (m per animation second), tone index.
  const particles = useMemo(() => {
    const m = geometry.length.length;
    let vehKm = 0;
    for (let e = 0; e < m; e++) vehKm += flow[e] * (geometry.length[e] / 1000);
    const small = typeof window !== "undefined" && window.innerWidth < 900;
    const target = small ? 3000 : 6000;
    const perParticle = Math.max(vehKm / target, 1);
    const random = seeded(m);
    const edges: number[] = [];
    const toneList: number[] = [];
    for (let e = 0; e < m; e++) {
      if (flow[e] <= 0 || geometry.length[e] <= 0) continue;
      const exact = (flow[e] * (geometry.length[e] / 1000)) / perParticle;
      const n = Math.floor(exact) + (random() < exact % 1 ? 1 : 0);
      for (let k = 0; k < n; k++) {
        edges.push(e);
        toneList.push(tones[e]);
      }
    }
    const count = edges.length;
    const edge = Int32Array.from(edges);
    const toneIdx = Uint8Array.from(toneList);
    const dist = new Float64Array(count);
    const speed = new Float32Array(count);
    for (let i = 0; i < count; i++) {
      const e = edge[i];
      dist[i] = random() * geometry.length[e];
      const minutes = Math.max(time[e], 0.05);
      speed[i] = (geometry.length[e] / minutes) * SIM_MINUTES_PER_SECOND;
    }
    return { count, edge, toneIdx, dist, speed };
  }, [geometry, flow, time, tones]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !map || !enabled) {
      const ctx = canvas?.getContext("2d");
      if (canvas && ctx) ctx.clearRect(0, 0, canvas.width, canvas.height);
      return;
    }
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    const { start, lon, lat, cum, nx, ny, length } = geometry;
    const { count, edge, toneIdx, dist, speed } = particles;
    const edgeStreet = data.graph.edges.street;

    let dpr = 1;
    const resize = () => {
      dpr = window.devicePixelRatio || 1;
      const { clientWidth, clientHeight } = canvas;
      canvas.width = Math.round(clientWidth * dpr);
      canvas.height = Math.round(clientHeight * dpr);
    };
    resize();
    const observer = new ResizeObserver(resize);
    observer.observe(canvas);

    // Trails are cleared while the map moves so they don't smear across the screen.
    let moving = false;
    const onMoveStart = () => {
      moving = true;
    };
    const onMoveEnd = () => {
      moving = false;
    };
    map.on("movestart", onMoveStart);
    map.on("moveend", onMoveEnd);

    const xs = new Float32Array(count);
    const ys = new Float32Array(count);
    let last = performance.now();
    let frame = 0;
    const tick = (now: number) => {
      const dt = Math.min((now - last) / 1000, 0.05);
      last = now;
      const zoom = map.getZoom();
      const offset = Math.max(0.8, Math.min(5, (zoom - 10) * 0.9 + 1)) * dpr;
      const size = Math.max(2.4, Math.min(5, (zoom - 9) * 0.85)) * dpr;
      const w = canvas.width;
      const h = canvas.height;

      if (moving) ctx.clearRect(0, 0, w, h);
      else {
        ctx.globalCompositeOperation = "destination-out";
        ctx.fillStyle = "rgba(0, 0, 0, 0.2)";
        ctx.fillRect(0, 0, w, h);
        ctx.globalCompositeOperation = "source-over";
      }

      for (let i = 0; i < count; i++) {
        const e = edge[i];
        const len = length[e];
        let d = dist[i] + speed[i] * dt;
        if (d >= len) d -= len * Math.floor(d / len);
        dist[i] = d;
        let k = start[e];
        const end = start[e + 1] - 1;
        while (k < end - 1 && cum[k + 1] < d) k++;
        const segLen = cum[k + 1] - cum[k] || 1;
        const f = (d - cum[k]) / segLen;
        const p = map.project([lon[k] + (lon[k + 1] - lon[k]) * f, lat[k] + (lat[k + 1] - lat[k]) * f]);
        xs[i] = p.x * dpr + nx[k] * offset;
        ys[i] = p.y * dpr + ny[k] * offset;
      }

      const focus = focusRef.current;
      for (const inFocus of focus === null ? [true] : [false, true]) {
        ctx.globalAlpha = inFocus ? 1 : 0.18;
        for (let t = 0; t < TONES.length; t++) {
          ctx.fillStyle = TONE_COLORS[TONES[t]];
          ctx.beginPath();
          for (let i = 0; i < count; i++) {
            if (toneIdx[i] !== t) continue;
            if (focus !== null && (edgeStreet[edge[i]] === focus) !== inFocus) continue;
            const x = xs[i];
            const y = ys[i];
            if (x < -4 || y < -4 || x > w + 4 || y > h + 4) continue;
            ctx.rect(x - size / 2, y - size / 2, size, size);
          }
          ctx.fill();
        }
      }
      ctx.globalAlpha = 1;
      frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);

    return () => {
      cancelAnimationFrame(frame);
      observer.disconnect();
      map.off("movestart", onMoveStart);
      map.off("moveend", onMoveEnd);
      ctx.clearRect(0, 0, canvas.width, canvas.height);
    };
  }, [map, enabled, geometry, particles, data]);

  return <canvas ref={canvasRef} className={styles.particles} aria-hidden="true" />;
}
