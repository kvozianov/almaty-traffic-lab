import { effectiveCapacity, type CityModel, type LinkParams } from "./model";
import type { Metrics, StreetDelta } from "./types";

export const CONGESTED_VC = 0.9;

/**
 * CO2 grams per vehicle-km as a function of average speed: slower, stop-and-go
 * traffic burns more fuel per km. A smooth proxy curve (~165 g/km at 50 km/h,
 * ~340 g/km at 10 km/h), not a COPERT calculation.
 */
export function co2GramsPerKm(speedKmh: number): number {
  return 120 + 2200 / Math.max(speedKmh, 5);
}

export function computeMetrics(
  model: CityModel,
  params: LinkParams,
  flow: Float64Array,
  time: Float64Array,
  totalTrips: number,
  unservedTrips: number,
): { metrics: Metrics; vc: Float64Array } {
  const m = model.edgeCount;
  const vc = new Float64Array(m);
  let tt = 0;
  let vkm = 0;
  let congested = 0;
  let co2 = 0;
  for (let i = 0; i < m; i++) {
    const km = model.length[i] / 1000;
    if (params.closed[i]) continue;
    vc[i] = flow[i] / effectiveCapacity(params, i);
    tt += flow[i] * time[i];
    vkm += flow[i] * km;
    if (vc[i] > CONGESTED_VC && !params.detour[i]) congested += km;
    const speed = time[i] > 0 ? km / (time[i] / 60) : 0;
    co2 += flow[i] * km * co2GramsPerKm(speed);
  }
  const trips = totalTrips - unservedTrips;
  const vehHours = tt / 60;
  return {
    vc,
    metrics: {
      trips,
      unservedTrips,
      avgTripMin: trips > 0 ? tt / trips : 0,
      vehHours,
      vehKm: vkm,
      avgSpeedKmh: vehHours > 0 ? vkm / vehHours : 0,
      congestedKm: congested,
      co2Tonnes: co2 / 1e6,
    },
  };
}

/** Vehicle-km and flow-weighted minutes-per-km for every named street. */
function streetTotals(model: CityModel, flow: Float64Array, time: Float64Array, exclude?: Uint8Array) {
  const count = model.graph.streets.length;
  const vkm = new Float64Array(count);
  const minutes = new Float64Array(count);
  for (let i = 0; i < model.edgeCount; i++) {
    const s = model.street[i];
    if (s < 0 || exclude?.[i]) continue;
    vkm[s] += flow[i] * (model.length[i] / 1000);
    minutes[s] += flow[i] * time[i];
  }
  return { vkm, minutes };
}

/** Streets whose traffic changed most between baseline and scenario. */
export function streetDeltas(
  model: CityModel,
  base: { flow: Float64Array; time: Float64Array },
  next: { flow: Float64Array; time: Float64Array },
  changedStreets: Set<number>,
  minBaseVehKm = 50,
  /** Links whose scenario traffic is not on the street itself (closed roads used as side-street detours). */
  detour?: Uint8Array,
): StreetDelta[] {
  const a = streetTotals(model, base.flow, base.time);
  const b = streetTotals(model, next.flow, next.time, detour);
  const out: StreetDelta[] = [];
  for (let s = 0; s < model.graph.streets.length; s++) {
    const before = a.vkm[s];
    const after = b.vkm[s];
    if (before < minBaseVehKm && after < minBaseVehKm) continue;
    out.push({
      street: s,
      name: model.graph.streets[s].name,
      vehKmDelta: after - before,
      trafficPct: before > 0 ? ((after - before) / before) * 100 : 100,
      delayBefore: before > 0 ? a.minutes[s] / before : 0,
      delayAfter: after > 0 ? b.minutes[s] / after : 0,
      changed: changedStreets.has(s),
    });
  }
  out.sort((x, y) => Math.abs(y.vehKmDelta) - Math.abs(x.vehKmDelta) || x.street - y.street);
  return out;
}
