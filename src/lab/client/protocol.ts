import type { Convergence, Metrics, PeriodId, Scenario, StreetDelta } from "../engine/types";
import type { RunPassport } from "../engine";

/** Messages from the page to the engine worker. */
export type WorkerRequest =
  | { type: "init"; baseUrl: string }
  | { type: "baseline"; period: PeriodId }
  | { type: "run"; id: number; scenario: Scenario };

export interface RunResult {
  id: number;
  scenario: Scenario;
  baseline: Metrics;
  metrics: Metrics;
  convergence: Convergence;
  /** Per directed edge, vehicles per hour. */
  baseFlow: Float64Array;
  flow: Float64Array;
  /** Per directed edge, demand / capacity. */
  vc: Float64Array;
  streets: StreetDelta[];
  passport: RunPassport;
}

/** Messages from the engine worker to the page. */
export type WorkerResponse =
  | { type: "ready"; dataHash: string }
  | { type: "baselineReady"; period: PeriodId; ms: number }
  | { type: "progress"; id: number; stage: "baseline" | "routing"; iteration: number; gap: number }
  | { type: "result"; result: RunResult }
  | { type: "error"; id?: number; message: string };
