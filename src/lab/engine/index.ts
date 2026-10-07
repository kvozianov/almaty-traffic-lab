import type { AssignOptions } from "./assign";
import { assignPaths, type RouteSet } from "./paths";
import { buildDemand } from "./demand";
import { computeMetrics, streetDeltas } from "./metrics";
import { linkParams, type CityModel } from "./model";
import { applyChanges, canonicalJson, sha256Hex } from "./scenario";
import type { AssignmentResult, Metrics, Scenario, StreetDelta } from "./types";

export const ENGINE_VERSION = "2.0.0";

export * from "./types";
export { buildModel } from "./model";
export type { CityModel } from "./model";
export {
  applyChanges,
  canonicalJson,
  decodeScenario,
  emptyScenario,
  encodeScenario,
  isChangeAvailable,
  PERIODS,
  sha256Hex,
} from "./scenario";
export { DEVELOPMENT_RATES } from "./demand";

export type RunOptions = AssignOptions & { warmStart?: RouteSet };

export function runAssignment(
  model: CityModel,
  scenario: Scenario,
  options: RunOptions = {},
): AssignmentResult & { routes: RouteSet } {
  const started = performance.now();
  const params = linkParams(model, applyChanges(model, scenario.changes));
  const demand = buildDemand(model, scenario.period, scenario.changes);
  const out = assignPaths(model, params, demand, options);
  const { metrics, vc } = computeMetrics(model, params, out.flow, out.time, demand.totalTrips, out.unservedTrips);
  return {
    metrics,
    vc,
    flow: out.flow,
    time: out.time,
    convergence: { iterations: out.iterations, relativeGap: out.relativeGap, ms: performance.now() - started },
    routes: out.routes,
  };
}

export interface Comparison {
  baseline: AssignmentResult;
  scenario: AssignmentResult;
  streets: StreetDelta[];
}

/** Streets touched by the scenario's section changes. */
export function changedStreets(model: CityModel, scenario: Scenario): Set<number> {
  const out = new Set<number>();
  for (const c of scenario.changes) {
    if (c.type !== "development") {
      const s = model.graph.sections[c.section];
      if (s) out.add(s.street);
    }
  }
  return out;
}

export function compare(
  model: CityModel,
  scenario: Scenario,
  baseline: AssignmentResult & { routes: RouteSet },
  options: AssignOptions = {},
): Comparison {
  const result = runAssignment(model, scenario, { warmStart: baseline.routes, ...options });
  return {
    baseline,
    scenario: result,
    streets: streetDeltas(model, baseline, result, changedStreets(model, scenario), 50, applyChanges(model, scenario.changes).closed),
  };
}

function roundMetrics(metrics: Metrics): Record<string, number> {
  return Object.fromEntries(Object.entries(metrics).map(([k, v]) => [k, Math.round(v * 1e6) / 1e6]));
}

export interface RunPassport {
  engineVersion: string;
  dataHash: string;
  scenarioHash: string;
  resultHash: string;
}

export async function passport(dataHash: string, scenario: Scenario, metrics: Metrics): Promise<RunPassport> {
  const scenarioHash = await sha256Hex(canonicalJson({ engine: ENGINE_VERSION, dataHash, scenario }));
  const resultHash = await sha256Hex(canonicalJson({ scenarioHash, metrics: roundMetrics(metrics) }));
  return { engineVersion: ENGINE_VERSION, dataHash, scenarioHash, resultHash };
}
