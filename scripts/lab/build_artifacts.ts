/**
 * Precomputes baseline flows for every period (so the map is coloured on first
 * paint) and writes public/model/manifest.json with SHA-256 hashes of all inputs.
 * The browser recomputes the same baseline in a worker; the engine tests check
 * that both agree.
 *
 *   npx tsx scripts/lab/build_artifacts.ts
 */
import { createHash } from "node:crypto";
import { readFileSync, writeFileSync } from "node:fs";
import { buildModel, canonicalJson, emptyScenario, ENGINE_VERSION, PERIODS, runAssignment } from "../../src/lab/engine";
import type { Calibration, RawCityGraph, RawDemand } from "../../src/lab/engine";

const DIR = "public/model";
const sha = (bytes: Buffer | string) => createHash("sha256").update(bytes).digest("hex");

const files = ["city-graph.json", "demand.json", "calibration.json"] as const;
const raw = Object.fromEntries(files.map((f) => [f, readFileSync(`${DIR}/${f}`)])) as Record<(typeof files)[number], Buffer>;
const graph = JSON.parse(raw["city-graph.json"].toString("utf8")) as RawCityGraph;
const demand = JSON.parse(raw["demand.json"].toString("utf8")) as RawDemand;
const calibration = JSON.parse(raw["calibration.json"].toString("utf8")) as Calibration;
const model = buildModel(graph, demand, calibration);

const inputs = Object.fromEntries(files.map((f) => [f, { sha256: sha(raw[f]), bytes: raw[f].length }]));
const dataHash = sha(canonicalJson(inputs));

const baseline: Record<string, { flow: number[]; metrics: unknown; iterations: number; relativeGap: number }> = {};
for (const period of PERIODS) {
  const r = runAssignment(model, emptyScenario(period));
  baseline[period] = {
    flow: Array.from(r.flow, (v) => Math.round(v)),
    metrics: r.metrics,
    iterations: r.convergence.iterations,
    relativeGap: r.convergence.relativeGap,
  };
  console.log(
    `${period}: ${r.convergence.iterations} it, gap ${r.convergence.relativeGap.toExponential(1)}, ` +
      `${r.metrics.avgSpeedKmh.toFixed(1)} km/h, ${r.metrics.avgTripMin.toFixed(1)} min, ${r.convergence.ms.toFixed(0)} ms`,
  );
}
const baselineJson = JSON.stringify({ engineVersion: ENGINE_VERSION, dataHash, periods: baseline });
writeFileSync(`${DIR}/baseline.json`, baselineJson);

const manifest = {
  schema: "almaty-traffic-lab/manifest/v1",
  engineVersion: ENGINE_VERSION,
  dataHash,
  osmTimestamp: graph.source.osmTimestamp,
  attribution: graph.source.attribution,
  license: graph.source.license,
  claimLevels: { roads: "real-data", signals: "real-data", capacities: "proxy", demand: "proxy", calibration: "proxy" },
  inputs,
  outputs: { "baseline.json": { sha256: sha(baselineJson), bytes: Buffer.byteLength(baselineJson) } },
  stats: graph.stats,
};
writeFileSync(`${DIR}/manifest.json`, JSON.stringify(manifest, null, 2) + "\n");
console.log(`dataHash ${dataHash}`);
