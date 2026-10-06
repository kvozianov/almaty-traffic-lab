import type { Zone } from "./demand";
import { MinHeap } from "./heap";
import { BPR_ALPHA, type CityModel, type LinkParams } from "./model";

/** Congested travel time (minutes) on edge i with flow v: BPR + fixed signal delay. */
export function edgeTime(p: LinkParams, i: number, v: number): number {
  const r = v / p.cap[i];
  const r2 = r * r;
  return p.t0[i] * (1 + BPR_ALPHA * r2 * r2) + p.delay[i];
}

/** d t / d v of the BPR term. */
export function edgeTimeDerivative(p: LinkParams, i: number, v: number): number {
  const c = p.cap[i];
  const r = v / c;
  return (4 * BPR_ALPHA * p.t0[i] * r * r * r) / c;
}

/**
 * Multi-source Dijkstra from a zone's connector nodes (initial distance =
 * access time). Ties break on node index, so trees are identical everywhere.
 */
export class ShortestPathTree {
  readonly dist: Float64Array;
  readonly pred: Int32Array;
  /** Nodes in settle order; `settled` entries are valid. */
  readonly order: Int32Array;
  settled = 0;
  private heap: MinHeap;

  constructor(private model: CityModel) {
    const n = model.nodeCount;
    this.dist = new Float64Array(n);
    this.pred = new Int32Array(n);
    this.order = new Int32Array(n);
    this.heap = new MinHeap(n * 2);
  }

  build(origin: Zone, cost: Float64Array, closed: Uint8Array): void {
    const { dist, pred, order, heap } = this;
    const { outStart, outEdges, edgeTo } = this.model;
    dist.fill(Infinity);
    pred.fill(-1);
    heap.clear();
    for (const [node, access] of origin.connectors) {
      if (access < dist[node]) {
        dist[node] = access;
        heap.push(access, node);
      }
    }
    let settled = 0;
    while (heap.size > 0) {
      const d = heap.peekKey();
      const u = heap.peekNode();
      heap.pop();
      if (d > dist[u]) continue;
      order[settled++] = u;
      for (let k = outStart[u]; k < outStart[u + 1]; k++) {
        const e = outEdges[k];
        if (closed[e]) continue;
        const v = edgeTo[e];
        const nd = d + cost[e];
        if (nd < dist[v]) {
          dist[v] = nd;
          pred[v] = e;
          heap.push(nd, v);
        }
      }
    }
    this.settled = settled;
  }

  /** Same as build(), but computes congested edge times from flows on the fly. */
  buildFromFlows(origin: Zone, params: LinkParams, flow: Float64Array): void {
    const { dist, pred, order, heap } = this;
    const { outStart, outEdges, edgeTo } = this.model;
    const { closed, t0, cap, delay } = params;
    dist.fill(Infinity);
    pred.fill(-1);
    heap.clear();
    for (const [node, access] of origin.connectors) {
      if (access < dist[node]) {
        dist[node] = access;
        heap.push(access, node);
      }
    }
    let settled = 0;
    while (heap.size > 0) {
      const d = heap.peekKey();
      const u = heap.peekNode();
      heap.pop();
      if (d > dist[u]) continue;
      order[settled++] = u;
      for (let k = outStart[u]; k < outStart[u + 1]; k++) {
        const e = outEdges[k];
        if (closed[e]) continue;
        const v = edgeTo[e];
        const r = flow[e] / cap[e];
        const r2 = r * r;
        const nd = d + (t0[e] * (1 + BPR_ALPHA * r2 * r2) + delay[e]);
        if (nd < dist[v]) {
          dist[v] = nd;
          pred[v] = e;
          heap.push(nd, v);
        }
      }
    }
    this.settled = settled;
  }

  /** Best connector of the destination zone: [node, total cost incl. both accesses], node -1 if unreachable. */
  bestDestination(dest: Zone): [number, number, number] {
    let bestNode = -1;
    let best = Infinity;
    let bestAccess = 0;
    for (const [node, access] of dest.connectors) {
      const c = this.dist[node] + access;
      if (c < best || (c === best && node < bestNode)) {
        best = c;
        bestNode = node;
        bestAccess = access;
      }
    }
    return [bestNode, best, bestAccess];
  }

  /** Edge list of the tree path ending at `node`, from the origin side. */
  pathTo(node: number): Int32Array {
    const { pred } = this;
    const { edgeFrom } = this.model;
    let count = 0;
    for (let v = node; pred[v] >= 0; v = edgeFrom[pred[v]]) count++;
    const edges = new Int32Array(count);
    let k = count;
    for (let v = node; pred[v] >= 0; v = edgeFrom[pred[v]]) edges[--k] = pred[v];
    return edges;
  }

  /** True when `edges` is exactly the tree path ending at `node` (no allocation). */
  treePathEquals(node: number, edges: Int32Array): boolean {
    const { pred } = this;
    const { edgeFrom } = this.model;
    let k = edges.length - 1;
    let v = node;
    while (pred[v] >= 0) {
      if (k < 0 || edges[k] !== pred[v]) return false;
      v = edgeFrom[pred[v]];
      k--;
    }
    return k === -1;
  }

  /** Origin access time paid at the first node of the path to `node`. */
  originAccess(node: number): number {
    const { pred } = this;
    const { edgeFrom } = this.model;
    let v = node;
    while (pred[v] >= 0) v = edgeFrom[pred[v]];
    return this.dist[v];
  }
}
