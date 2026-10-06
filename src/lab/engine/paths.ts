import type { AssignOptions, AssignOutput } from "./assign";
import type { DemandSet } from "./demand";
import type { CityModel, LinkParams } from "./model";
import { edgeTime, edgeTimeDerivative, ShortestPathTree } from "./shortest";

/**
 * Path-based user equilibrium by gradient projection (Jayakrishnan et al., 1994).
 *
 * Every origin-destination pair keeps the set of routes it uses. Each
 * iteration finds the current fastest route per pair and shifts trips from
 * slower routes onto it, by the cost difference divided by the curvature.
 * Converges in far fewer iterations than Frank-Wolfe and, crucially, a
 * scenario can start from the baseline's routes: only trips whose route is
 * affected have to move.
 */

/**
 * Relative gap at which the lab stops. Tested: a no-change scenario started
 * from a baseline at this gap moves average trip time by <0.01 % and no road
 * by more than 5 % / 50 vehicles, which is below what the interface shows.
 */
export const DEFAULT_GAP = 5e-4;

export interface Route {
  edges: Int32Array;
  /** Origin + destination access minutes (constant for the route). */
  access: number;
  flow: number;
}

/** Routes keyed by origin * KEY_STRIDE + destination. */
export type RouteSet = Map<number, Route[]>;

const KEY_STRIDE = 1 << 16;

export interface PathAssignOutput extends AssignOutput {
  routes: RouteSet;
}

export function assignPaths(
  model: CityModel,
  params: LinkParams,
  demand: DemandSet,
  options: AssignOptions & { warmStart?: RouteSet } = {},
): PathAssignOutput {
  const maxIterations = options.maxIterations ?? 100;
  const gapTarget = options.gapTarget ?? DEFAULT_GAP;
  const m = model.edgeCount;
  const { closed } = params;
  const tree = new ShortestPathTree(model);
  const x = new Float64Array(m);
  // Congested time and its derivative per edge, kept in sync with x so route
  // costs are cheap sums. Only edges whose flow changes are recomputed.
  const cost = new Float64Array(m);
  const deriv = new Float64Array(m);
  const markBest = new Int32Array(m);
  const markRoute = new Int32Array(m);
  let stamp = 0;

  for (let e = 0; e < m; e++) {
    cost[e] = edgeTime(params, e, 0);
    deriv[e] = 0;
  }
  const addFlow = (edges: Int32Array, delta: number) => {
    for (let i = 0; i < edges.length; i++) {
      const e = edges[i];
      const v = x[e] + delta;
      x[e] = v;
      cost[e] = edgeTime(params, e, v);
      deriv[e] = edgeTimeDerivative(params, e, v);
    }
  };
  const routeCost = (r: Route) => {
    let c = r.access;
    const edges = r.edges;
    for (let i = 0; i < edges.length; i++) c += cost[edges[i]];
    return c;
  };
  // Routes inherited from the warm start that cross a closed road. New routes
  // come from shortest-path trees, which never use closed edges.
  const blocked = new Set<Route>();
  const crossesClosed = (edges: Int32Array) => {
    for (let i = 0; i < edges.length; i++) if (closed[edges[i]]) return true;
    return false;
  };

  // Initial routes: copy the warm start for pairs that still exist.
  const routes: RouteSet = new Map();
  const trips = new Map<number, number>();
  for (let o = 0; o < demand.zones.length; o++) {
    for (let k = demand.odStart[o]; k < demand.odStart[o + 1]; k++) {
      const key = o * KEY_STRIDE + demand.odDest[k];
      trips.set(key, demand.odTrips[k]);
      const warm = options.warmStart?.get(key);
      if (!warm) continue;
      const total = warm.reduce((s, r) => s + r.flow, 0);
      if (total <= 0) continue;
      const scale = demand.odTrips[k] / total;
      const copy = warm.map((r) => ({ edges: r.edges, access: r.access, flow: r.flow * scale }));
      routes.set(key, copy);
      for (const r of copy) {
        addFlow(r.edges, r.flow);
        if (crossesClosed(r.edges)) blocked.add(r);
      }
    }
  }

  let unserved = 0;
  let iterations = 0;
  let gap = Infinity;
  while (iterations < maxIterations) {
    let excess = 0;
    let total = 0;
    // Trips loaded onto a pair's first route this iteration: the gap is not
    // meaningful until every pair has been loaded once.
    let freshLoads = 0;
    unserved = 0;

    for (let o = 0; o < demand.zones.length; o++) {
      const start = demand.odStart[o];
      const end = demand.odStart[o + 1];
      if (start === end) continue;
      tree.build(demand.zones[o], cost, closed);

      for (let k = start; k < end; k++) {
        const key = o * KEY_STRIDE + demand.odDest[k];
        const odTrips = trips.get(key)!;
        const [destNode, bestCost, destAccess] = tree.bestDestination(demand.zones[demand.odDest[k]]);
        let set = routes.get(key);
        if (destNode < 0) {
          // Unreachable after closures: drop the trips from the network.
          if (set) for (const r of set) addFlow(r.edges, -r.flow);
          routes.delete(key);
          unserved += odTrips;
          continue;
        }
        if (!set) {
          set = [];
          routes.set(key, set);
        }
        let best: Route | undefined;
        for (const r of set) {
          if (tree.treePathEquals(destNode, r.edges)) {
            best = r;
            break;
          }
        }
        if (!best) {
          best = { edges: tree.pathTo(destNode), access: tree.originAccess(destNode) + destAccess, flow: 0 };
          set.push(best);
        }
        if (set.length === 1) {
          if (best.flow === 0) {
            best.flow = odTrips;
            addFlow(best.edges, odTrips);
            freshLoads++;
          }
          total += odTrips * bestCost;
          continue;
        }

        // Gap contribution at the costs seen by this origin.
        for (const r of set) {
          if (r.flow <= 0) continue;
          if (blocked.has(r)) {
            total += r.flow * bestCost;
            excess += r.flow * bestCost; // stranded trips count fully towards the gap
          } else {
            const c = routeCost(r);
            excess += r.flow * (c - bestCost);
            total += r.flow * c;
          }
        }

        stamp++;
        const bestEdges = best.edges;
        for (let i = 0; i < bestEdges.length; i++) markBest[bestEdges[i]] = stamp;
        for (const r of set) {
          if (r === best || r.flow === 0) continue;
          let shift: number;
          if (blocked.has(r)) shift = r.flow;
          else {
            const edges = r.edges;
            for (let i = 0; i < edges.length; i++) markRoute[edges[i]] = stamp;
            let curvature = 0;
            for (let i = 0; i < edges.length; i++) if (markBest[edges[i]] !== stamp) curvature += deriv[edges[i]];
            for (let i = 0; i < bestEdges.length; i++) {
              if (markRoute[bestEdges[i]] !== stamp) curvature += deriv[bestEdges[i]];
            }
            const diff = routeCost(r) - routeCost(best);
            if (diff <= 0) continue;
            shift = curvature > 0 ? Math.min(r.flow, diff / curvature) : r.flow;
            stamp++;
            for (let i = 0; i < bestEdges.length; i++) markBest[bestEdges[i]] = stamp;
          }
          r.flow -= shift;
          best.flow += shift;
          addFlow(r.edges, -shift);
          addFlow(bestEdges, shift);
        }
        let dead = 0;
        for (const r of set) if (r.flow <= 1e-9 && r !== best) dead++;
        if (dead > 0) routes.set(key, set.filter((r) => r.flow > 1e-9 || r === best));
      }
    }

    iterations++;
    gap = total > 0 ? excess / total : 0;
    if (freshLoads > 0) gap = Math.max(gap, 1);
    options.onProgress?.(iterations, gap);
    if (gap < gapTarget) break;
  }

  // Clear floating-point dust (e.g. 1e-12 vehicles left on a closed road).
  for (let i = 0; i < m; i++) if (closed[i] || x[i] < 1e-6) x[i] = 0;
  const time = new Float64Array(m);
  for (let i = 0; i < m; i++) time[i] = edgeTime(params, i, x[i]);
  return { flow: x, time, iterations, relativeGap: gap, unservedTrips: unserved, routes };
}
