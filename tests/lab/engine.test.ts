import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { beforeAll, describe, expect, it } from "vitest";
import {
  buildModel,
  compare,
  decodeScenario,
  DEVELOPMENT_RATES,
  emptyScenario,
  encodeScenario,
  isChangeAvailable,
  passport,
  runAssignment,
  type CityModel,
  type RawCityGraph,
  type RawDemand,
  type Scenario,
} from "../../src/lab/engine";
import { assignFrankWolfe } from "../../src/lab/engine/assign";
import { buildDemand } from "../../src/lab/engine/demand";
import { linkParams } from "../../src/lab/engine/model";
import { DEFAULT_GAP } from "../../src/lab/engine/paths";
import { applyChanges } from "../../src/lab/engine/scenario";

const DIR = "public/lab";
const read = (f: string) => readFileSync(`${DIR}/${f}`);
const graph = JSON.parse(read("city-graph.json").toString()) as RawCityGraph;
const demand = JSON.parse(read("demand.json").toString()) as RawDemand;
const calibration = JSON.parse(read("calibration.json").toString());

let model: CityModel;
let baseline: ReturnType<typeof runAssignment>;

const streetId = (name: string) => graph.streets.findIndex((s) => s.name === name);
const sectionOf = (street: string, labelStart: string) =>
  graph.sections.findIndex((s) => s.street === streetId(street) && s.label.startsWith(labelStart));
const streetVehKm = (flow: Float64Array, street: number) => {
  let v = 0;
  for (let e = 0; e < model.edgeCount; e++) if (model.street[e] === street) v += flow[e] * model.length[e];
  return v / 1000;
};

beforeAll(() => {
  model = buildModel(graph, demand, calibration);
  baseline = runAssignment(model, emptyScenario("am"));
});

describe("data artifacts", () => {
  it("manifest hashes match the committed files", () => {
    const manifest = JSON.parse(read("manifest.json").toString());
    for (const [file, meta] of Object.entries<{ sha256: string }>({ ...manifest.inputs, ...manifest.outputs })) {
      expect(createHash("sha256").update(read(file)).digest("hex"), file).toBe(meta.sha256);
    }
  });

  it("road graph is one strongly connected network of the expected size", () => {
    expect(model.nodeCount).toBeGreaterThan(3000);
    expect(model.edgeCount).toBeGreaterThan(6000);
    expect(graph.stats.signals).toBeGreaterThan(600);
    for (let v = 0; v < model.nodeCount; v++) expect(model.outStart[v + 1]).toBeGreaterThan(model.outStart[v]);
  });

  it("most selectable sections carry a readable English street name", () => {
    const named = graph.sections.filter((s) => /^[A-Za-z0-9]/.test(graph.streets[s.street].name)).length;
    expect(named / graph.sections.length).toBeGreaterThan(0.97);
  });

  it("precomputed baseline flows equal what the engine computes", () => {
    const stored = JSON.parse(read("baseline.json").toString());
    const flow = stored.periods.am.flow as number[];
    for (let e = 0; e < model.edgeCount; e++) expect(flow[e]).toBe(Math.round(baseline.flow[e]));
  });
});

describe("equilibrium assignment", () => {
  it("converges below the target gap and routes every trip", () => {
    expect(baseline.convergence.relativeGap).toBeLessThan(DEFAULT_GAP);
    expect(baseline.metrics.unservedTrips).toBe(0);
    expect(baseline.metrics.trips).toBeCloseTo(calibration.totalTrips, -1);
  });

  it("keeps every origin-destination pair's trips on its routes", () => {
    const d = buildDemand(model, "am", []);
    let k = 0;
    for (let o = 0; o < d.zones.length; o++) {
      for (; k < d.odStart[o + 1]; k++) {
        const routes = baseline.routes.get(o * (1 << 16) + d.odDest[k])!;
        const sum = routes.reduce((s, r) => s + r.flow, 0);
        expect(sum).toBeCloseTo(d.odTrips[k], 6);
      }
    }
  });

  it("agrees with an independent conjugate Frank-Wolfe solver", () => {
    const params = linkParams(model, applyChanges(model, []));
    const fw = assignFrankWolfe(model, params, buildDemand(model, "am", []), { gapTarget: 2e-4, maxIterations: 400 });
    let ttFw = 0;
    let ttGp = 0;
    for (let e = 0; e < model.edgeCount; e++) {
      ttFw += fw.flow[e] * fw.time[e];
      ttGp += baseline.flow[e] * baseline.time[e];
    }
    expect(Math.abs(ttGp / ttFw - 1)).toBeLessThan(0.002);
  }, 60_000);

  it("is deterministic, including the run passport", async () => {
    const again = runAssignment(model, emptyScenario("am"));
    expect(Array.from(again.flow)).toEqual(Array.from(baseline.flow));
    const a = await passport("data", emptyScenario("am"), baseline.metrics);
    const b = await passport("data", emptyScenario("am"), again.metrics);
    expect(a).toEqual(b);
  });

  it("a no-change scenario started from the baseline stays put", () => {
    const c = compare(model, emptyScenario("am"), baseline);
    expect(Math.abs(c.scenario.metrics.avgTripMin / baseline.metrics.avgTripMin - 1)).toBeLessThan(1e-3);
    for (let e = 0; e < model.edgeCount; e++) {
      const d = Math.abs(c.scenario.flow[e] - baseline.flow[e]);
      expect(d < 50 || d / baseline.flow[e] < 0.05).toBe(true);
    }
  });
});

describe("interventions", () => {
  it("closing a section removes its traffic and pushes it onto parallel streets", () => {
    const section = sectionOf("Abay Avenue", "Baitursynuly");
    expect(section).toBeGreaterThanOrEqual(0);
    const scenario: Scenario = { v: 1, period: "am", changes: [{ type: "close", section }] };
    const c = compare(model, scenario, baseline);
    for (const e of graph.sections[section].edges) expect(c.scenario.flow[e]).toBe(0);
    const kurmangazy = streetId("Kurmangazy Street");
    expect(streetVehKm(c.scenario.flow, kurmangazy)).toBeGreaterThan(1.5 * streetVehKm(baseline.flow, kurmangazy));
    expect(c.scenario.metrics.vehHours).toBeGreaterThan(baseline.metrics.vehHours);
    expect(c.streets[0].changed || c.streets.some((s) => s.changed)).toBe(true);
  });

  it("a bus lane removes car capacity and is unavailable on single-lane sections", () => {
    const section = sectionOf("Abay Avenue", "Baitursynuly");
    const before = linkParams(model, applyChanges(model, []));
    const after = linkParams(model, applyChanges(model, [{ type: "busLane", section }]));
    for (const e of graph.sections[section].edges) expect(after.cap[e]).toBeLessThan(before.cap[e]);
    const single = graph.sections.findIndex((s) => s.minLanes === 1);
    expect(isChangeAvailable(model, "busLane", single)).toBe(false);
  });

  it("more green for one street costs the crossing approaches", () => {
    const section = sectionOf("Abay Avenue", "Baitursynuly");
    const before = linkParams(model, applyChanges(model, []));
    const after = linkParams(model, applyChanges(model, [{ type: "greenWave", section }]));
    const own = graph.sections[section].edges.filter((e) => model.signal[e]);
    expect(own.length).toBeGreaterThan(0);
    for (const e of own) expect(after.delay[e]).toBeLessThan(before.delay[e]);
    let worse = 0;
    for (let e = 0; e < model.edgeCount; e++) if (after.delay[e] > before.delay[e]) worse++;
    expect(worse).toBeGreaterThan(0);
  });

  it("a new housing estate adds the expected number of trips", () => {
    const size = 3000;
    const scenario: Scenario = {
      v: 1,
      period: "am",
      changes: [{ type: "development", kind: "housing", lon: 76.86, lat: 43.21, size }],
    };
    const c = compare(model, scenario, baseline);
    const added = c.scenario.metrics.trips - baseline.metrics.trips;
    expect(added).toBeCloseTo(size * DEVELOPMENT_RATES.housing.perUnit.am, 0);
    expect(c.scenario.metrics.vehHours).toBeGreaterThan(baseline.metrics.vehHours);
  });

  it("a scenario finishes quickly from the warm start", () => {
    const section = sectionOf("Abay Avenue", "Zharokov");
    const c = compare(model, { v: 1, period: "am", changes: [{ type: "close", section }] }, baseline);
    expect(c.scenario.convergence.iterations).toBeLessThan(15);
    expect(c.scenario.convergence.ms).toBeLessThan(3000);
  });
});

describe("scenario links", () => {
  it("round-trips through the URL encoding", () => {
    const scenario: Scenario = {
      v: 1,
      period: "pm",
      changes: [
        { type: "close", section: 12 },
        { type: "speedLimit", section: 40, kmh: 40 },
        { type: "development", kind: "office", lon: 76.9, lat: 43.25, size: 2000 },
      ],
    };
    expect(decodeScenario(encodeScenario(scenario), graph.sections.length)).toEqual(scenario);
  });

  it("rejects malformed or out-of-range scenarios", () => {
    const bad = (s: unknown) => Buffer.from(JSON.stringify(s)).toString("base64url");
    expect(decodeScenario("not-base64!", 10)).toBeNull();
    expect(decodeScenario(bad({ v: 1, period: "am", changes: [{ type: "close", section: 99 }] }), 10)).toBeNull();
    expect(decodeScenario(bad({ v: 2, period: "am", changes: [] }), 10)).toBeNull();
    expect(decodeScenario(bad({ v: 1, period: "am", changes: [{ type: "explode", section: 1 }] }), 10)).toBeNull();
  });
});
