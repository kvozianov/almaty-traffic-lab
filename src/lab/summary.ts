import type { RunResult } from "./client/protocol";
import type { Change, Metrics, PeriodId, RawCityGraph, StreetDelta } from "./engine/types";
import { DEVELOPMENT_LABELS, formatInt, percentChange, PERIOD_LABELS } from "./format";

function subject(graph: RawCityGraph, change: Change): string {
  if (change.type === "development") {
    return `${formatInt(change.size)} new ${DEVELOPMENT_LABELS[change.kind].unit}`.replace("new m²", "m²");
  }
  const street = graph.streets[graph.sections[change.section].street].name;
  switch (change.type) {
    case "close":
      return `Closing ${street}`;
    case "busLane":
      return `A bus lane on ${street}`;
    case "addLane":
      return `Widening ${street}`;
    case "greenWave":
      return `Signal priority on ${street}`;
    case "speedLimit":
      return `A ${change.kmh} km/h limit on ${street}`;
  }
}

/** Streets that changed meaningfully, excluding ones the user edited. */
export function notableStreets(streets: StreetDelta[], limit = 6): StreetDelta[] {
  return streets
    .filter((s) => Math.abs(s.trafficPct) >= 3 && Math.abs(s.vehKmDelta) >= 40)
    .slice(0, limit);
}

/** One or two plain-English sentences describing a result. */
export function headline(graph: RawCityGraph, result: Pick<RunResult, "scenario" | "baseline" | "metrics" | "streets">): string {
  const { scenario, baseline, metrics } = result;
  const changes = scenario.changes;
  // Several changes of one kind on one street read as a single change.
  const subjects = [...new Set(changes.map((c) => subject(graph, c)))];
  const lead = subjects.length === 1 ? subjects[0] : `These ${changes.length} changes`;
  const verb = subjects.length === 1 && !/^\d/.test(lead) ? "makes" : "make";
  const period = PERIOD_LABELS[scenario.period].short.toLowerCase();
  const pct = percentChange(baseline.avgTripMin, metrics.avgTripMin);
  const rounded = Math.abs(pct).toFixed(1);
  let first: string;
  if (Math.abs(pct) < 0.05) first = `${lead} barely ${verb === "make" ? "change" : "changes"} the average ${period} trip.`;
  else if (pct > 0) first = `${lead} ${verb} the average ${period} trip ${rounded}% longer.`;
  else first = `${lead} ${verb} the average ${period} trip ${rounded}% shorter.`;

  const other = notableStreets(result.streets).find((s) => !s.changed);
  if (!other) return first;
  const amount = Math.abs(other.trafficPct).toFixed(0);
  return other.trafficPct > 0
    ? `${first} ${other.name} takes ${amount}% more traffic.`
    : `${first} ${other.name} gets ${amount}% less traffic.`;
}

export interface MetricRow {
  key: keyof Metrics;
  label: string;
  unit: string;
  digits: number;
  /** Lower is better for every metric shown. */
  hint: string;
}

export const METRIC_ROWS: MetricRow[] = [
  { key: "avgTripMin", label: "Average trip on main roads", unit: "min", digits: 1, hint: "Minutes per car trip." },
  { key: "vehHours", label: "Time spent driving", unit: "vehicle-hours", digits: 0, hint: "All cars, during the hour." },
  { key: "congestedKm", label: "Congested roads", unit: "km", digits: 1, hint: "Lanes over 90% of capacity." },
  { key: "co2Tonnes", label: "CO₂ from traffic", unit: "t", digits: 1, hint: "Speed-dependent estimate." },
];

export function periodLabel(period: PeriodId): string {
  return `${PERIOD_LABELS[period].long} · ${PERIOD_LABELS[period].time}`;
}
