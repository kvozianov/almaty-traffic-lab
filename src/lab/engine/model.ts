import type { Calibration, RawCityGraph, RawDemand } from "./types";

/** Minutes of uniform (Webster) delay at a signal: 0.5 * cycle * (1 - g)^2. */
export const SIGNAL_CYCLE_S = 90;
export const DEFAULT_GREEN = 0.5;
export const BPR_ALPHA = 0.15;
export const ACCESS_SPEED_KMH = 20;

export function signalDelayMin(green: number): number {
  const red = 1 - green;
  return (0.5 * SIGNAL_CYCLE_S * red * red) / 60;
}

/**
 * Immutable network + demand prepared for repeated assignments. Built once per
 * page load from the JSON artifacts; scenarios only patch link parameters.
 */
export interface CityModel {
  graph: RawCityGraph;
  demand: RawDemand;
  calibration: Calibration;
  nodeCount: number;
  edgeCount: number;
  edgeFrom: Int32Array;
  edgeTo: Int32Array;
  /** CSR adjacency: out edges of node v are outEdges[outStart[v] .. outStart[v + 1]). */
  outStart: Int32Array;
  outEdges: Int32Array;
  length: Float64Array;
  freeSpeed: Float64Array;
  lanes: Float64Array;
  capPerLane: Float64Array;
  /** 1 when the edge ends at a signalised node. */
  signal: Uint8Array;
  street: Int32Array;
  section: Int32Array;
  /** Signal-group id of the edge's end node, or -1. */
  signalGroup: Int32Array;
  /** Lon/lat of nodes. */
  lon: Float64Array;
  lat: Float64Array;
}

export function buildModel(graph: RawCityGraph, demand: RawDemand, calibration: Calibration): CityModel {
  const n = graph.nodes.lon.length;
  const e = graph.edges;
  const m = e.from.length;

  const outStart = new Int32Array(n + 1);
  for (let i = 0; i < m; i++) outStart[e.from[i] + 1]++;
  for (let v = 0; v < n; v++) outStart[v + 1] += outStart[v];
  const fill = outStart.slice(0, n);
  const outEdges = new Int32Array(m);
  for (let i = 0; i < m; i++) outEdges[fill[e.from[i]]++] = i;

  const signal = new Uint8Array(m);
  const signalGroup = new Int32Array(m);
  for (let i = 0; i < m; i++) {
    signal[i] = graph.nodes.signal[e.to[i]] ? 1 : 0;
    signalGroup[i] = graph.nodes.signalGroup[e.to[i]];
  }

  return {
    graph,
    demand,
    calibration,
    nodeCount: n,
    edgeCount: m,
    edgeFrom: Int32Array.from(e.from),
    edgeTo: Int32Array.from(e.to),
    outStart,
    outEdges,
    length: Float64Array.from(e.length),
    freeSpeed: Float64Array.from(e.freeSpeed),
    lanes: Float64Array.from(e.lanes),
    capPerLane: Float64Array.from(e.capPerLane),
    signal,
    street: Int32Array.from(e.street),
    section: Int32Array.from(e.section),
    signalGroup,
    lon: Float64Array.from(graph.nodes.lon),
    lat: Float64Array.from(graph.nodes.lat),
  };
}

/** Per-scenario link parameters. */
export interface LinkParams {
  /** Free-flow time, minutes. */
  t0: Float64Array;
  /** Capacity, vehicles per hour. */
  cap: Float64Array;
  /** Fixed signal delay, minutes. */
  delay: Float64Array;
  closed: Uint8Array;
}

export interface LinkInputs {
  lanes: Float64Array;
  freeSpeed: Float64Array;
  green: Float64Array;
  closed: Uint8Array;
}

export function baseLinkInputs(model: CityModel): LinkInputs {
  return {
    lanes: model.lanes.slice(),
    freeSpeed: model.freeSpeed.slice(),
    green: new Float64Array(model.edgeCount).fill(DEFAULT_GREEN),
    closed: new Uint8Array(model.edgeCount),
  };
}

export function linkParams(model: CityModel, inputs: LinkInputs): LinkParams {
  const m = model.edgeCount;
  const t0 = new Float64Array(m);
  const cap = new Float64Array(m);
  const delay = new Float64Array(m);
  for (let i = 0; i < m; i++) {
    t0[i] = model.length[i] / 1000 / inputs.freeSpeed[i] * 60;
    const green = model.signal[i] ? inputs.green[i] : 1;
    cap[i] = Math.max(1, inputs.lanes[i] * model.capPerLane[i] * green);
    delay[i] = model.signal[i] ? signalDelayMin(inputs.green[i]) : 0;
  }
  return { t0, cap, delay, closed: inputs.closed.slice() };
}

/** Metres per degree at Almaty's latitude (43.24°), fixed so results are identical in every browser. */
const M_PER_DEG_LON = 81_095.6;
const M_PER_DEG_LAT = 111_132.0;

/**
 * Equirectangular distance in metres. Accurate to <0.1 % inside the city and
 * uses only +, *, sqrt (correctly rounded in IEEE 754), so it is deterministic.
 */
export function distanceM(lon1: number, lat1: number, lon2: number, lat2: number): number {
  const dx = (lon2 - lon1) * M_PER_DEG_LON;
  const dy = (lat2 - lat1) * M_PER_DEG_LAT;
  return Math.sqrt(dx * dx + dy * dy);
}

/** Nearest nodes with at least one outgoing edge, ties broken by index. */
export function nearestNodes(model: CityModel, lon: number, lat: number, count: number): number[] {
  const scored: [number, number][] = [];
  for (let v = 0; v < model.nodeCount; v++) {
    if (model.outStart[v + 1] === model.outStart[v]) continue;
    scored.push([distanceM(lon, lat, model.lon[v], model.lat[v]), v]);
  }
  scored.sort((a, b) => a[0] - b[0] || a[1] - b[1]);
  return scored.slice(0, count).map(([, v]) => v);
}
