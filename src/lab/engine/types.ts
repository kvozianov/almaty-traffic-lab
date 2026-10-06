/** Raw JSON shapes produced by scripts/lab/*.py. */

export interface RawCityGraph {
  schema: "almaty-traffic-lab/city-graph/v1";
  source: { snapshot: string; osmTimestamp: string | null; license: string; attribution: string };
  params: { coordScale: number };
  stats: Record<string, number>;
  nodes: { lon: number[]; lat: number[]; signal: number[]; signalGroup: number[] };
  edges: {
    from: number[];
    to: number[];
    length: number[];
    freeSpeed: number[];
    lanes: number[];
    capPerLane: number[];
    cls: number[];
    street: number[];
    section: number[];
    seg: number[];
    rev: number[];
  };
  geometry: { offset: number[]; coords: number[] };
  classes: string[];
  streets: { name: string; nameLocal: string | null }[];
  sections: RawSection[];
}

export interface RawSection {
  street: number;
  label: string;
  lengthM: number;
  edges: number[];
  minLanes: number;
  signals: number;
  bbox: [number, number, number, number];
}

export type PeriodId = "am" | "midday" | "pm" | "night";

export interface RawDemand {
  schema: "almaty-traffic-lab/demand/v1";
  claimLevel: "proxy";
  method: Record<string, unknown>;
  periods: Record<PeriodId, { label: string; factor: number; transpose: boolean | "mix" }>;
  zones: { center: [number, number]; production: number; attraction: number; connectors: [number, number][] }[];
  /** [origin zone, destination zone, share of all trips] */
  matrix: [number, number, number][];
}

export interface Calibration {
  /** Car trips on the main road network in the morning peak hour. */
  totalTrips: number;
  note: string;
}

/* ------------------------------------------------------------ scenario */

export type SectionChangeType = "close" | "busLane" | "addLane" | "greenWave" | "speedLimit";
export type DevelopmentKind = "housing" | "office" | "mall";

export type Change =
  | { type: Exclude<SectionChangeType, "speedLimit">; section: number }
  | { type: "speedLimit"; section: number; kmh: number }
  | { type: "development"; kind: DevelopmentKind; lon: number; lat: number; size: number };

export interface Scenario {
  v: 1;
  period: PeriodId;
  changes: Change[];
}

/* ------------------------------------------------------------ results */

export interface Metrics {
  /** Car trips that found a route. */
  trips: number;
  unservedTrips: number;
  /** Average minutes spent on the main road network per trip. */
  avgTripMin: number;
  vehHours: number;
  vehKm: number;
  avgSpeedKmh: number;
  /** Directional road-km where demand exceeds 90 % of capacity. */
  congestedKm: number;
  co2Tonnes: number;
}

export interface Convergence {
  iterations: number;
  relativeGap: number;
  ms: number;
}

export interface AssignmentResult {
  metrics: Metrics;
  convergence: Convergence;
  /** Per directed edge. */
  flow: Float64Array;
  /** Per directed edge: demand / capacity (Infinity for closed edges with flow 0 -> 0). */
  vc: Float64Array;
  /** Per directed edge: congested travel time in minutes. */
  time: Float64Array;
}

export interface StreetDelta {
  street: number;
  name: string;
  /** Change in vehicle-km on the street, percent of baseline. */
  trafficPct: number;
  /** Change in vehicle-km, absolute. */
  vehKmDelta: number;
  /** Average minutes per km, baseline -> scenario. */
  delayBefore: number;
  delayAfter: number;
  changed: boolean;
}
