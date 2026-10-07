import type { Zone } from "./demand";
import { MinHeap } from "./heap";
import { ANALYSIS_PERIOD_H, BPR_ALPHA, SIGNAL_CYCLE_S, type CityModel, type LinkParams } from "./model";

const CYCLE_MIN = SIGNAL_CYCLE_S / 60;
const T = ANALYSIS_PERIOD_H;

/**
 * Congested travel time (minutes) on edge i with flow v.
 *
 * Mid-block: BPR curve on the full lane capacity. At a signalised link end:
 * HCM 2000 control delay = uniform delay d1 (Webster, grows as the green fills)
 * + incremental delay d2 (the queue that builds when demand nears or exceeds the
 * approach capacity over the analysis period). Uses only +, ×, ÷ and sqrt, so it
 * is deterministic across browsers.
 */
export function edgeTime(p: LinkParams, i: number, v: number): number {
  const r = v / p.cap[i];
  const r2 = r * r;
  const link = p.t0[i] * (1 + BPR_ALPHA * r2 * r2);
  const c = p.sigCap[i];
  if (c === 0) return link;
  const g = p.green[i];
  const x = v / c;
  const red = 1 - g;
  const d1 = (0.5 * CYCLE_MIN * red * red) / (1 - (x < 1 ? x : 1) * g);
  const xm = x - 1;
  const d2 = 15 * T * (xm + Math.sqrt(xm * xm + (4 * x) / (c * T))); // HCM: 900·T seconds = 15·T minutes
  return link + d1 + d2;
}

/** d t / d v of edgeTime. */
export function edgeTimeDerivative(p: LinkParams, i: number, v: number): number {
  const cap = p.cap[i];
  const r = v / cap;
  let d = (4 * BPR_ALPHA * p.t0[i] * r * r * r) / cap;
  const c = p.sigCap[i];
  if (c === 0) return d;
  const g = p.green[i];
  const x = v / c;
  const red = 1 - g;
  if (x < 1) {
    const q = 1 - x * g;
    d += (0.5 * CYCLE_MIN * red * red * g) / (q * q) / c;
  }
  const xm = x - 1;
  const k = 4 / (c * T);
  d += (15 * T * (1 + (xm + k / 2) / Math.sqrt(xm * xm + k * x))) / c;
  return d;
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
