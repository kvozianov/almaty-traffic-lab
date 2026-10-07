/**
 * Calibrates the demand model against published Almaty measurements
 * (public/model/observations.json):
 *
 *   - corridor speeds by period (Sergek ITS, a year-long Abay commute log),
 *   - the weekday congestion profile (Yandex Traffic points per period),
 *
 * by fitting four numbers: the gravity distance decay `beta` (grid), the
 * morning-peak trip total, and the midday and evening volumes relative to the
 * morning. The fitted values, every observed-vs-model pair and a hold-out check
 * against Sergek's top-15 congested junctions go to public/model/calibration.json.
 *
 *   npx tsx scripts/lab/calibrate.ts            # full fit (several minutes)
 */
import { execFileSync } from "node:child_process";
import { mkdtempSync, readFileSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { buildModel, emptyScenario, runAssignment } from "../../src/lab/engine";
import type { Calibration, PeriodId, RawCityGraph, RawDemand } from "../../src/lab/engine";
import {
  corridorEdges,
  corridorSpeed,
  freeFlowTimes,
  junctionChecks,
  pointsToTravelTimeIndex,
  travelTimeIndex,
  type Observations,
} from "../../src/lab/engine/observed";

const DIR = "public/model";
const BETAS = [0.12, 0.15, 0.18];
const NIGHT_FACTOR = 0.15;
const TTI_WEIGHT = 1;

const graph = JSON.parse(readFileSync(`${DIR}/city-graph.json`, "utf8")) as RawCityGraph;
const obs = JSON.parse(readFileSync(`${DIR}/observations.json`, "utf8")) as Observations;
const fitTargets = obs.corridorSpeeds.filter((t) => t.use === "fit");
const targetEdges = new Map(fitTargets.map((t) => [t.id, corridorEdges(graph, t)]));
for (const [id, edges] of targetEdges) if (edges.length === 0) throw new Error(`no edges for target ${id}`);
const ttiTarget = Object.fromEntries(obs.timeProfile.points.map((p) => [p.period, pointsToTravelTimeIndex(p.points)])) as Record<
  PeriodId,
  number
>;

const tmp = mkdtempSync(join(tmpdir(), "lab-calibrate-"));
function demandFor(beta: number): RawDemand {
  const out = join(tmp, `demand-${beta}.json`);
  execFileSync("python3", ["scripts/lab/build_demand.py", "--beta", String(beta), "--out", out], { stdio: "pipe" });
  return JSON.parse(readFileSync(out, "utf8")) as RawDemand;
}

type Evaluation = {
  error: number;
  tti: number;
  speeds: Record<string, number>;
  flow: Float64Array;
  time: Float64Array;
};

function evaluate(demand: RawDemand, totalTrips: number, factor: number, period: PeriodId): Evaluation {
  const model = buildModel(graph, demand, { totalTrips, periodFactors: { [period]: factor }, note: "" });
  const r = runAssignment(model, emptyScenario(period));
  const free = freeFlowTimes(model);
  const tti = travelTimeIndex(r.flow, r.time, free);
  let error = TTI_WEIGHT * Math.log(tti / ttiTarget[period]) ** 2;
  const speeds: Record<string, number> = {};
  for (const t of fitTargets) {
    if (t.period !== period) continue;
    const v = corridorSpeed(model, targetEdges.get(t.id)!, r.time);
    speeds[t.id] = v;
    error += t.weight * Math.log(v / t.speedKmh) ** 2;
  }
  return { error, tti, speeds, flow: r.flow, time: r.time };
}

function median(values: number[]): number {
  const v = [...values].sort((a, b) => a - b);
  const mid = Math.floor(v.length / 2);
  return v.length % 2 ? v[mid] : (v[mid - 1] + v[mid]) / 2;
}

/** Golden-section search on a 1-D objective (unimodal enough for demand scale). */
function golden(f: (x: number) => number, lo: number, hi: number, iterations = 11): number {
  const g = (Math.sqrt(5) - 1) / 2;
  let a = lo;
  let b = hi;
  let c = b - g * (b - a);
  let d = a + g * (b - a);
  let fc = f(c);
  let fd = f(d);
  for (let i = 0; i < iterations; i++) {
    if (fc < fd) {
      b = d;
      d = c;
      fd = fc;
      c = b - g * (b - a);
      fc = f(c);
    } else {
      a = c;
      c = d;
      fc = fd;
      d = a + g * (b - a);
      fd = f(d);
    }
  }
  return (a + b) / 2;
}

const results: { beta: number; total: number; midday: number; pm: number; error: number }[] = [];
for (const beta of BETAS) {
  const demand = demandFor(beta);
  const total = Math.round(golden((x) => evaluate(demand, x, 1, "am").error, 100_000, 350_000) / 1000) * 1000;
  const am = evaluate(demand, total, 1, "am");
  const midday = Number(golden((x) => evaluate(demand, total, x, "midday").error, 0.3, 1.2).toFixed(3));
  const pm = Number(golden((x) => evaluate(demand, total, x, "pm").error, 0.6, 1.8).toFixed(3));
  const error = am.error + evaluate(demand, total, midday, "midday").error + evaluate(demand, total, pm, "pm").error;
  results.push({ beta, total, midday, pm, error });
  console.log(`beta=${beta} total=${total} midday=${midday} pm=${pm} error=${error.toFixed(4)}`);
}

const best = results.reduce((a, b) => (b.error < a.error ? b : a));
const demand = demandFor(best.beta);
const factors: Record<PeriodId, number> = { am: 1, midday: best.midday, pm: best.pm, night: NIGHT_FACTOR };

// Final report: every observation next to the model value.
const fit: { id: string; label: string; period: PeriodId; hours: string; observed: number; model: number; unit: string; source: string }[] = [];
let pmRun: Evaluation | null = null;
for (const period of ["am", "midday", "pm", "night"] as PeriodId[]) {
  const e = evaluate(demand, best.total, factors[period], period);
  if (period === "pm") pmRun = e;
  const p = obs.timeProfile.points.find((x) => x.period === period)!;
  fit.push({
    id: `tti-${period}`,
    label: `City-wide congestion, ${p.hours}`,
    period,
    hours: p.hours,
    observed: Number(ttiTarget[period].toFixed(2)),
    model: Number(e.tti.toFixed(2)),
    unit: "travel time index",
    source: obs.timeProfile.source,
  });
  for (const t of fitTargets.filter((x) => x.period === period)) {
    fit.push({
      id: t.id,
      label: t.label,
      period,
      hours: t.hours,
      observed: t.speedKmh,
      model: Number(e.speeds[t.id].toFixed(1)),
      unit: "km/h",
      source: t.source,
    });
  }
}

const model = buildModel(graph, demand, { totalTrips: best.total, periodFactors: factors, note: "" });
const checks = junctionChecks(model, pmRun!.flow, pmRun!.time, freeFlowTimes(model), obs.congestedJunctions.ranked);
const found = checks.filter((c) => c.percentile !== null);
const top10 = found.filter((c) => c.percentile! >= 0.9).length;
const top25 = found.filter((c) => c.percentile! >= 0.75).length;
const medianPct = found.length > 0 ? median(found.map((c) => c.percentile!)) : null;
const errors = fit.filter((f) => f.unit === "km/h").map((f) => Math.abs(f.model / f.observed - 1));

const calibration: Calibration & Record<string, unknown> = {
  totalTrips: best.total,
  periodFactors: factors,
  beta: best.beta,
  note:
    "Fitted to published Almaty measurements (observations.json): corridor speeds from Sergek ITS and a " +
    "year-long Abay Avenue commute log, and the Yandex Traffic weekday profile. Night volume is assumed.",
  fit,
  speedErrorMedian: Number(median(errors).toFixed(3)),
  validation: {
    description: "Hold-out: Sergek ITS top-15 congested junctions (Feb 2025), ranked by modelled evening delay.",
    matched: found.length,
    inTop10Percent: top10,
    inTop25Percent: top25,
    medianPercentile: medianPct === null ? null : Number(medianPct.toFixed(3)),
    junctions: checks.map((c) => ({ ...c, percentile: c.percentile === null ? null : Number(c.percentile.toFixed(3)) })),
  },
  search: results,
};
writeFileSync(`${DIR}/calibration.json`, JSON.stringify(calibration, null, 2) + "\n");
console.log(JSON.stringify({ best, fit, validation: calibration.validation }, null, 2));
