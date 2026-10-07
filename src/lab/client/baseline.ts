import type { PeriodId } from "../engine/types";
import type { CityData } from "./data";

/** Base capacity per directed edge, matching the engine's default link parameters. */
export function baseCapacity(data: CityData): Float64Array {
  const { edges, nodes } = data.graph;
  const out = new Float64Array(edges.from.length);
  for (let e = 0; e < out.length; e++) {
    const green = nodes.signal[edges.to[e]] ? 0.5 : 1;
    out[e] = Math.max(1, edges.lanes[e] * edges.capPerLane[e] * green);
  }
  return out;
}

const vcCache = new WeakMap<CityData, Map<PeriodId, Float64Array>>();
export function baselineFlow(data: CityData, period: PeriodId): number[] {
  return data.baseline.periods[period].flow;
}

/** Congested travel time per edge (minutes) for today's baseline, precomputed by the engine. */
export function baselineTime(data: CityData, period: PeriodId): number[] {
  return data.baseline.periods[period].time;
}

export function baselineVc(data: CityData, period: PeriodId): Float64Array {
  let byPeriod = vcCache.get(data);
  if (!byPeriod) {
    byPeriod = new Map();
    vcCache.set(data, byPeriod);
  }
  let vc = byPeriod.get(period);
  if (!vc) {
    const cap = baseCapacity(data);
    const flow = baselineFlow(data, period);
    vc = Float64Array.from(flow, (f, e) => f / cap[e]);
    byPeriod.set(period, vc);
  }
  return vc;
}

export function sectionStats(data: CityData, period: PeriodId, section: number) {
  const s = data.graph.sections[section];
  const flow = baselineFlow(data, period);
  const vc = baselineVc(data, period);
  let maxFlow = 0;
  let maxVc = 0;
  for (const e of s.edges) {
    maxFlow = Math.max(maxFlow, flow[e]);
    maxVc = Math.max(maxVc, vc[e]);
  }
  return { maxFlow, maxVc, lanes: s.lanes, signals: s.signals, lengthM: s.lengthM };
}

export function streetBbox(data: CityData, street: number): [number, number, number, number] | null {
  let box: [number, number, number, number] | null = null;
  for (const s of data.graph.sections) {
    if (s.street !== street) continue;
    box = box
      ? [Math.min(box[0], s.bbox[0]), Math.min(box[1], s.bbox[1]), Math.max(box[2], s.bbox[2]), Math.max(box[3], s.bbox[3])]
      : [...s.bbox];
  }
  return box;
}
