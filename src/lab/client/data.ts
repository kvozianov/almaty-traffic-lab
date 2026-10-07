"use client";

import { useEffect, useState } from "react";
import type { Metrics, PeriodId, RawCityGraph } from "../engine/types";

export const DATA_URL = "/model";

export interface BaselineFile {
  engineVersion: string;
  dataHash: string;
  periods: Record<PeriodId, { flow: number[]; time: number[]; metrics: Metrics }>;
}

export interface Manifest {
  engineVersion: string;
  dataHash: string;
  osmTimestamp: string | null;
  attribution: string;
  stats: Record<string, number>;
}

/** Graph prepared for drawing: one decoded polyline per directed edge. */
export interface CityData {
  graph: RawCityGraph;
  baseline: BaselineFile;
  manifest: Manifest;
  /** Polyline of each directed edge in travel direction. */
  paths: [number, number][][];
  /** Lower-cased "street · section" strings for search. */
  searchIndex: string[];
}

function decodePaths(graph: RawCityGraph): [number, number][][] {
  const { offset, coords } = graph.geometry;
  const scale = graph.params.coordScale;
  const segments: [number, number][][] = [];
  for (let s = 0; s + 1 < offset.length; s++) {
    const pts: [number, number][] = [];
    for (let k = offset[s]; k < offset[s + 1]; k++) pts.push([coords[2 * k] / scale, coords[2 * k + 1] / scale]);
    segments.push(pts);
  }
  const { seg, rev } = graph.edges;
  return seg.map((s, e) => (rev[e] ? segments[s].slice().reverse() : segments[s]));
}

let cache: Promise<CityData> | null = null;

export function loadCityData(): Promise<CityData> {
  if (!cache) {
    cache = Promise.all([
      fetch(`${DATA_URL}/city-graph.json`).then((r) => r.json() as Promise<RawCityGraph>),
      fetch(`${DATA_URL}/baseline.json`).then((r) => r.json() as Promise<BaselineFile>),
      fetch(`${DATA_URL}/manifest.json`).then((r) => r.json() as Promise<Manifest>),
    ]).then(([graph, baseline, manifest]) => ({
      graph,
      baseline,
      manifest,
      paths: decodePaths(graph),
      searchIndex: graph.sections.map((s) => `${graph.streets[s.street].name} ${s.label}`.toLowerCase()),
    }));
    cache.catch(() => {
      cache = null;
    });
  }
  return cache;
}

export function useCityData(): { data: CityData | null; error: string | null } {
  const [data, setData] = useState<CityData | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    let alive = true;
    loadCityData()
      .then((d) => alive && setData(d))
      .catch((e: unknown) => alive && setError(e instanceof Error ? e.message : "Could not load the city data."));
    return () => {
      alive = false;
    };
  }, []);
  return { data, error };
}
