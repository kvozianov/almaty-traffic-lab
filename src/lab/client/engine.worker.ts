/// <reference lib="webworker" />
import {
  buildModel,
  compare,
  emptyScenario,
  passport,
  runAssignment,
  type AssignmentResult,
  type Calibration,
  type CityModel,
  type PeriodId,
  type RawCityGraph,
  type RawDemand,
} from "../engine";
import type { RouteSet } from "../engine/paths";
import type { RunResult, WorkerRequest, WorkerResponse } from "./protocol";

declare const self: DedicatedWorkerGlobalScope;

let model: CityModel | null = null;
let dataHash = "";
const baselines = new Map<PeriodId, AssignmentResult & { routes: RouteSet }>();
let queue: Promise<unknown> = Promise.resolve();

const post = (message: WorkerResponse, transfer: Transferable[] = []) => self.postMessage(message, transfer);

async function fetchJson<T>(url: string): Promise<T> {
  const response = await fetch(url);
  if (!response.ok) throw new Error(`Could not load ${url} (${response.status})`);
  return (await response.json()) as T;
}

function baselineFor(period: PeriodId, id = -1) {
  let base = baselines.get(period);
  if (!base) {
    const started = performance.now();
    base = runAssignment(model!, emptyScenario(period), {
      onProgress: (iteration, gap) => post({ type: "progress", id, stage: "baseline", iteration, gap }),
    });
    baselines.set(period, base);
    post({ type: "baselineReady", period, ms: performance.now() - started });
  }
  return base;
}

/** Requests run one at a time so a run never races a baseline computation. */
function enqueue(task: () => Promise<void> | void) {
  queue = queue.then(task).catch((error: unknown) => {
    post({ type: "error", message: error instanceof Error ? error.message : String(error) });
  });
}

self.onmessage = (event: MessageEvent<WorkerRequest>) => {
  const message = event.data;
  switch (message.type) {
    case "init":
      enqueue(async () => {
        const base = message.baseUrl;
        const [graph, demand, calibration, manifest] = await Promise.all([
          fetchJson<RawCityGraph>(`${base}/city-graph.json`),
          fetchJson<RawDemand>(`${base}/demand.json`),
          fetchJson<Calibration>(`${base}/calibration.json`),
          fetchJson<{ dataHash: string }>(`${base}/manifest.json`),
        ]);
        model = buildModel(graph, demand, calibration);
        dataHash = manifest.dataHash;
        post({ type: "ready", dataHash });
      });
      break;
    case "baseline":
      enqueue(() => {
        baselineFor(message.period);
      });
      break;
    case "run":
      enqueue(async () => {
        const { id, scenario } = message;
        try {
          const base = baselineFor(scenario.period, id);
          const c = compare(model!, scenario, base, {
            onProgress: (iteration, gap) => post({ type: "progress", id, stage: "routing", iteration, gap }),
          });
          const result: RunResult = {
            id,
            scenario,
            baseline: base.metrics,
            metrics: c.scenario.metrics,
            convergence: c.scenario.convergence,
            baseFlow: base.flow.slice(),
            flow: c.scenario.flow,
            vc: c.scenario.vc,
            streets: c.streets.slice(0, 40),
            passport: await passport(dataHash, scenario, c.scenario.metrics),
          };
          post({ type: "result", result }, [result.baseFlow.buffer, result.flow.buffer, result.vc.buffer]);
        } catch (error) {
          post({ type: "error", id, message: error instanceof Error ? error.message : String(error) });
        }
      });
      break;
  }
};
