import { ACCESS_SPEED_KMH, distanceM, nearestNodes, type CityModel } from "./model";
import type { Change, DevelopmentKind, PeriodId } from "./types";

/**
 * Peak-hour car trips generated per unit of a new development and the share
 * that leaves the site, by period. Rough planning rates (proxy), see /methods.
 */
export const DEVELOPMENT_RATES: Record<
  DevelopmentKind,
  { unit: string; perUnit: Record<PeriodId, number>; outShare: Record<PeriodId, number> }
> = {
  housing: {
    unit: "apartments",
    perUnit: { am: 0.3, midday: 0.15, pm: 0.3, night: 0.03 },
    outShare: { am: 0.8, midday: 0.5, pm: 0.3, night: 0.5 },
  },
  office: {
    unit: "employees",
    perUnit: { am: 0.35, midday: 0.14, pm: 0.35, night: 0.02 },
    outShare: { am: 0.15, midday: 0.5, pm: 0.85, night: 0.5 },
  },
  mall: {
    unit: "m² of shops",
    perUnit: { am: 0.004, midday: 0.015, pm: 0.02, night: 0.002 },
    outShare: { am: 0.5, midday: 0.5, pm: 0.5, night: 0.5 },
  },
};

export interface Zone {
  /** [node, access minutes] */
  connectors: [number, number][];
}

/** Trips grouped by origin zone (CSR): destinations of zone o are at odStart[o]..odStart[o+1]. */
export interface DemandSet {
  zones: Zone[];
  odStart: Int32Array;
  odDest: Int32Array;
  odTrips: Float64Array;
  totalTrips: number;
}

function nearestZone(model: CityModel, lon: number, lat: number): number {
  let best = 0;
  let bestD = Infinity;
  model.demand.zones.forEach((z, i) => {
    const d = distanceM(lon, lat, z.center[0], z.center[1]);
    if (d < bestD) {
      bestD = d;
      best = i;
    }
  });
  return best;
}

export function buildDemand(model: CityModel, period: PeriodId, changes: Change[]): DemandSet {
  const raw = model.demand;
  const p = raw.periods[period];
  const total = model.calibration.totalTrips * p.factor;
  const baseZones = raw.zones.length;

  // pairs[o] -> Map(dest -> trips)
  const pairs: Map<number, number>[] = [];
  const add = (o: number, d: number, trips: number) => {
    if (trips <= 0 || o === d) return;
    while (pairs.length <= Math.max(o, d)) pairs.push(new Map());
    pairs[o].set(d, (pairs[o].get(d) ?? 0) + trips);
  };

  for (const [o, d, share] of raw.matrix) {
    const trips = share * total;
    if (p.transpose === true) add(d, o, trips);
    else if (p.transpose === "mix") {
      add(o, d, trips / 2);
      add(d, o, trips / 2);
    } else add(o, d, trips);
  }

  // Row/column distributions of the base AM matrix, used for new developments.
  const zones: Zone[] = raw.zones.map((z) => ({ connectors: z.connectors.map(([n, t]) => [n, t]) }));
  const developments = changes.filter((c): c is Extract<Change, { type: "development" }> => c.type === "development");
  if (developments.length > 0) {
    const rowSum = new Float64Array(baseZones);
    const colSum = new Float64Array(baseZones);
    for (const [o, d, s] of raw.matrix) {
      rowSum[o] += s;
      colSum[d] += s;
    }
    for (const dev of developments) {
      const rate = DEVELOPMENT_RATES[dev.kind];
      const trips = dev.size * rate.perUnit[period];
      const out = trips * rate.outShare[period];
      const inbound = trips - out;
      const anchor = nearestZone(model, dev.lon, dev.lat);
      const site = zones.length;
      zones.push({
        connectors: nearestNodes(model, dev.lon, dev.lat, 2).map((node) => [
          node,
          distanceM(dev.lon, dev.lat, model.lon[node], model.lat[node]) / 1000 / ACCESS_SPEED_KMH * 60,
        ]),
      });
      for (const [o, d, s] of raw.matrix) {
        if (o === anchor && rowSum[anchor] > 0) add(site, d, (out * s) / rowSum[anchor]);
        if (d === anchor && colSum[anchor] > 0) add(o, site, (inbound * s) / colSum[anchor]);
      }
    }
  }
  while (pairs.length < zones.length) pairs.push(new Map());

  const odStart = new Int32Array(zones.length + 1);
  let count = 0;
  for (let o = 0; o < zones.length; o++) {
    odStart[o] = count;
    count += pairs[o].size;
  }
  odStart[zones.length] = count;
  const odDest = new Int32Array(count);
  const odTrips = new Float64Array(count);
  let k = 0;
  let sum = 0;
  for (let o = 0; o < zones.length; o++) {
    const dests = [...pairs[o].keys()].sort((a, b) => a - b);
    for (const d of dests) {
      odDest[k] = d;
      odTrips[k] = pairs[o].get(d)!;
      sum += odTrips[k];
      k++;
    }
  }
  return { zones, odStart, odDest, odTrips, totalTrips: sum };
}
