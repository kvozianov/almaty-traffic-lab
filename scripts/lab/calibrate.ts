/**
 * Plausibility calibration of the demand scale (NOT a calibration against
 * observed counts). Finds the morning-peak trip total at which the main road
 * network reaches a target average speed, then writes public/lab/calibration.json.
 *
 *   npx tsx scripts/lab/calibrate.ts [--target-speed 27]
 */
import { readFileSync, writeFileSync } from "node:fs";
import { buildModel, emptyScenario, runAssignment } from "../../src/lab/engine";
import type { Calibration, RawCityGraph, RawDemand } from "../../src/lab/engine";

const args = process.argv.slice(2);
const targetSpeed = Number(args[args.indexOf("--target-speed") + 1] || 27);

const graph = JSON.parse(readFileSync("public/lab/city-graph.json", "utf8")) as RawCityGraph;
const demand = JSON.parse(readFileSync("public/lab/demand.json", "utf8")) as RawDemand;

function evaluate(totalTrips: number) {
  const model = buildModel(graph, demand, { totalTrips, note: "" });
  const r = runAssignment(model, emptyScenario("am"));
  let km = 0;
  for (let i = 0; i < model.edgeCount; i++) km += model.length[i] / 1000;
  return { ...r.metrics, congestedShare: r.metrics.congestedKm / km, convergence: r.convergence };
}

let lo = 10_000;
let hi = 300_000;
for (let k = 0; k < 14; k++) {
  const mid = Math.round((lo + hi) / 2);
  const r = evaluate(mid);
  console.log(
    `trips=${mid} speed=${r.avgSpeedKmh.toFixed(1)} avgTrip=${r.avgTripMin.toFixed(1)}min ` +
      `congested=${(r.congestedShare * 100).toFixed(1)}% iters=${r.convergence.iterations} ` +
      `gap=${r.convergence.relativeGap.toExponential(1)} ${r.convergence.ms.toFixed(0)}ms`,
  );
  if (r.avgSpeedKmh > targetSpeed) lo = mid;
  else hi = mid;
}
const totalTrips = Math.round((lo + hi) / 2 / 1000) * 1000;
const calibration: Calibration = {
  totalTrips,
  note:
    `Plausibility scale: morning-peak car trips on the main network chosen so that the average ` +
    `network speed is about ${targetSpeed} km/h. Not fitted to observed counts.`,
};
writeFileSync("public/lab/calibration.json", JSON.stringify(calibration, null, 2) + "\n");
console.log("final", totalTrips, evaluate(totalTrips));
