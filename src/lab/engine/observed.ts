import { edgeTime } from "./shortest";
import { linkParams, baseLinkInputs, type CityModel } from "./model";
import type { PeriodId, RawCityGraph } from "./types";

/** Shapes of public/model/observations.json. */
export interface Observations {
  sources: { id: string; title: string; publisher: string; date: string; url: string }[];
  structure: {
    source: string;
    centre: { description: string; bbox: [number, number, number, number] };
    jobsInCentreShare: number;
    residentsOutsideCentreShare: number;
    carTripShare: number;
  };
  timeProfile: { source: string; scale: string; points: { period: PeriodId; hours: string; points: number }[] };
  corridorSpeeds: CorridorTarget[];
  congestedJunctions: { source: string; use: "validate"; ranked: [string, string][] };
}

export interface CorridorTarget {
  id: string;
  label: string;
  street: string;
  direction: "east" | "west" | "north" | "south" | "both";
  between?: [string, string];
  period: PeriodId;
  hours: string;
  speedKmh: number;
  source: string;
  weight: number;
  use: "fit" | "validate";
}

/**
 * Yandex reports congestion in points (0–10). We read a point as roughly 10 %
 * extra travel time over free flow, so 5 points ≈ travel time index 1.5. This
 * mapping is an assumption, stated wherever the profile is shown.
 */
export function pointsToTravelTimeIndex(points: number): number {
  return 1 + points / 10;
}

/** Directed edges of a corridor target, in the measured direction and stretch. */
export function corridorEdges(graph: RawCityGraph, target: CorridorTarget): number[] {
  const street = graph.streets.findIndex((s) => s.name === target.street);
  if (street < 0) return [];
  let sections = graph.sections.map((s, i) => [s, i] as const).filter(([s]) => s.street === street).map(([, i]) => i);
  if (target.between) {
    const [from, to] = target.between;
    const start = sections.findIndex((i) => graph.sections[i].label.startsWith(from));
    const end = sections.findIndex((i) => graph.sections[i].label.endsWith(to));
    if (start >= 0 && end >= start) sections = sections.slice(start, end + 1);
  }
  const allowed = new Set(sections);
  const { from, to, section } = graph.edges;
  const { lon, lat } = graph.nodes;
  const out: number[] = [];
  for (let e = 0; e < from.length; e++) {
    if (!allowed.has(section[e])) continue;
    const dx = lon[to[e]] - lon[from[e]];
    const dy = lat[to[e]] - lat[from[e]];
    const ok =
      target.direction === "both" ||
      (target.direction === "east" && dx > 0) ||
      (target.direction === "west" && dx < 0) ||
      (target.direction === "north" && dy > 0) ||
      (target.direction === "south" && dy < 0);
    if (ok) out.push(e);
  }
  return out;
}

/** Corridor travel speed (km/h): total length over total congested time. */
export function corridorSpeed(model: CityModel, edges: number[], time: ArrayLike<number>): number {
  let km = 0;
  let minutes = 0;
  for (const e of edges) {
    km += model.length[e] / 1000;
    minutes += time[e];
  }
  return minutes > 0 ? km / (minutes / 60) : 0;
}

/** Free-flow travel time per edge (minutes), signal delay included, for today's network. */
export function freeFlowTimes(model: CityModel): Float64Array {
  const params = linkParams(model, baseLinkInputs(model));
  const out = new Float64Array(model.edgeCount);
  for (let e = 0; e < model.edgeCount; e++) out[e] = edgeTime(params, e, 0);
  return out;
}

/** City-wide travel time index: vehicle-weighted congested time over free-flow time. */
export function travelTimeIndex(flow: ArrayLike<number>, time: ArrayLike<number>, free: ArrayLike<number>): number {
  let congested = 0;
  let base = 0;
  for (let e = 0; e < free.length; e++) {
    congested += flow[e] * time[e];
    base += flow[e] * free[e];
  }
  return base > 0 ? congested / base : 1;
}

export interface JunctionCheck {
  streets: [string, string];
  /** Share of the model's junctions with less delay (1 = most delayed in the city). */
  percentile: number | null;
  rank: number | null;
}

/**
 * Hold-out check against a published list of congested junctions: where does
 * each one rank among all signalised junctions by modelled delay
 * (vehicle-minutes per hour lost on the approaches)?
 */
export function junctionChecks(
  model: CityModel,
  flow: ArrayLike<number>,
  time: ArrayLike<number>,
  free: ArrayLike<number>,
  junctions: [string, string][],
): JunctionCheck[] {
  const { graph } = model;
  const delayByGroup = new Map<number, number>();
  for (let e = 0; e < model.edgeCount; e++) {
    const g = model.signalGroup[e];
    if (g < 0) continue;
    delayByGroup.set(g, (delayByGroup.get(g) ?? 0) + flow[e] * Math.max(0, time[e] - free[e] + (model.signal[e] ? 0.1875 : 0)));
  }
  const sorted = [...delayByGroup.values()].sort((a, b) => a - b);
  const nodeStreets = new Map<number, Set<number>>();
  for (let e = 0; e < model.edgeCount; e++) {
    const s = model.street[e];
    if (s < 0) continue;
    for (const n of [model.edgeFrom[e], model.edgeTo[e]]) {
      if (!nodeStreets.has(n)) nodeStreets.set(n, new Set());
      nodeStreets.get(n)!.add(s);
    }
  }
  return junctions.map(([a, b]) => {
    const sa = graph.streets.findIndex((s) => s.name === a);
    const sb = graph.streets.findIndex((s) => s.name === b);
    const nodesA: number[] = [];
    const nodesB: number[] = [];
    for (const [n, streets] of nodeStreets) {
      if (streets.has(sa)) nodesA.push(n);
      if (streets.has(sb)) nodesB.push(n);
    }
    // Junction = signal groups of A's nodes within 120 m of a node of B.
    const groups = new Set<number>();
    for (const n of nodesA) {
      const g = graph.nodes.signalGroup[n];
      if (g < 0) continue;
      for (const m of nodesB) {
        const dx = (model.lon[n] - model.lon[m]) * 81_095.6;
        const dy = (model.lat[n] - model.lat[m]) * 111_132;
        if (dx * dx + dy * dy < 120 * 120) {
          groups.add(g);
          break;
        }
      }
    }
    if (groups.size === 0) return { streets: [a, b], percentile: null, rank: null };
    let best = 0;
    for (const g of groups) best = Math.max(best, delayByGroup.get(g) ?? 0);
    let below = 0;
    while (below < sorted.length && sorted[below] < best) below++;
    return { streets: [a, b], percentile: below / sorted.length, rank: sorted.length - below };
  });
}
