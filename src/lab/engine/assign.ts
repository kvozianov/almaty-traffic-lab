import type { DemandSet } from "./demand";
import type { CityModel, LinkParams } from "./model";
import { edgeTime, edgeTimeDerivative, ShortestPathTree } from "./shortest";

export { edgeTime, edgeTimeDerivative } from "./shortest";

export interface AssignOptions {
  maxIterations?: number;
  /** Stop when the relative gap falls below this value. */
  gapTarget?: number;
  onProgress?: (iteration: number, gap: number) => void;
}

export interface AssignOutput {
  flow: Float64Array;
  time: Float64Array;
  iterations: number;
  relativeGap: number;
  unservedTrips: number;
}

/** Loads every trip on its current shortest path; returns unserved trips. */
function allOrNothing(
  model: CityModel,
  params: LinkParams,
  demand: DemandSet,
  tree: ShortestPathTree,
  load: Float64Array,
  cost: Float64Array,
  out: Float64Array,
): number {
  out.fill(0);
  let unserved = 0;
  for (let o = 0; o < demand.zones.length; o++) {
    const start = demand.odStart[o];
    const end = demand.odStart[o + 1];
    if (start === end) continue;
    tree.build(demand.zones[o], cost, params.closed);
    for (let k = start; k < end; k++) {
      const [node] = tree.bestDestination(demand.zones[demand.odDest[k]]);
      if (node < 0) unserved += demand.odTrips[k];
      else load[node] += demand.odTrips[k];
    }
    // Push node loads back to the origin along the tree (reverse settle order).
    for (let k = tree.settled - 1; k >= 0; k--) {
      const v = tree.order[k];
      const l = load[v];
      if (l === 0) continue;
      load[v] = 0;
      const e = tree.pred[v];
      if (e < 0) continue;
      out[e] += l;
      load[model.edgeFrom[e]] += l;
    }
  }
  return unserved;
}

const CFW_DELTA = 0.01;

/**
 * Conjugate Frank-Wolfe (Mitradjieva & Lindberg, 2013). Link-based and simple,
 * but slow to converge; kept as an independent reference for tests.
 * The interactive lab uses the path-based solver in paths.ts.
 */
export function assignFrankWolfe(
  model: CityModel,
  params: LinkParams,
  demand: DemandSet,
  options: AssignOptions = {},
): AssignOutput {
  const maxIterations = options.maxIterations ?? 200;
  const gapTarget = options.gapTarget ?? 1e-4;
  const m = model.edgeCount;
  const tree = new ShortestPathTree(model);
  const load = new Float64Array(model.nodeCount);
  const cost = new Float64Array(m);
  const x = new Float64Array(m);
  const y = new Float64Array(m);
  const target = new Float64Array(m);

  for (let i = 0; i < m; i++) cost[i] = edgeTime(params, i, 0);
  const unserved = allOrNothing(model, params, demand, tree, load, cost, x);

  let hasTarget = false;
  let iterations = 0;
  let gap = Infinity;
  while (iterations < maxIterations) {
    let tstt = 0;
    for (let i = 0; i < m; i++) {
      cost[i] = edgeTime(params, i, x[i]);
      tstt += x[i] * cost[i];
    }
    allOrNothing(model, params, demand, tree, load, cost, y);
    let sptt = 0;
    for (let i = 0; i < m; i++) sptt += y[i] * cost[i];
    gap = tstt > 0 ? Math.max(0, (tstt - sptt) / tstt) : 0;
    iterations++;
    options.onProgress?.(iterations, gap);
    if (gap < gapTarget) break;

    // Conjugate direction: combine the previous target with the new AON solution.
    let alpha = 0;
    if (hasTarget) {
      let num = 0;
      let den = 0;
      for (let i = 0; i < m; i++) {
        const h = edgeTimeDerivative(params, i, x[i]);
        if (h === 0) continue;
        const dPrev = target[i] - x[i];
        const dNew = y[i] - x[i];
        num += dPrev * h * dNew;
        den += dPrev * h * (dNew - dPrev);
      }
      if (den !== 0) alpha = Math.min(Math.max(num / den, 0), 1 - CFW_DELTA);
    }
    for (let i = 0; i < m; i++) target[i] = alpha * target[i] + (1 - alpha) * y[i];
    hasTarget = true;

    // Bisection on the derivative of the Beckmann objective along target - x.
    const slope = (lambda: number) => {
      let s = 0;
      for (let i = 0; i < m; i++) {
        const dxi = target[i] - x[i];
        if (dxi !== 0) s += dxi * edgeTime(params, i, x[i] + lambda * dxi);
      }
      return s;
    };
    let lo = 0;
    let hi = 1;
    if (slope(1) <= 0) lo = 1;
    else {
      for (let k = 0; k < 30; k++) {
        const mid = (lo + hi) / 2;
        if (slope(mid) > 0) hi = mid;
        else lo = mid;
      }
    }
    for (let i = 0; i < m; i++) x[i] += lo * (target[i] - x[i]);
    if (lo === 1) hasTarget = false; // a full step loses conjugacy
  }

  const time = new Float64Array(m);
  for (let i = 0; i < m; i++) time[i] = edgeTime(params, i, x[i]);
  return { flow: x, time, iterations, relativeGap: gap, unservedTrips: unserved };
}
