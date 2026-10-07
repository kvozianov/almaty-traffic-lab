import type { Change, DevelopmentKind, PeriodId, RawCityGraph, SectionChangeType } from "./engine/types";

export const PERIOD_LABELS: Record<PeriodId, { short: string; long: string; time: string }> = {
  // Hours follow the Yandex Traffic weekday profile used for calibration.
  am: { short: "Morning", long: "Morning peak", time: "around 9 am" },
  midday: { short: "Midday", long: "Midday", time: "noon–5 pm" },
  pm: { short: "Evening", long: "Evening peak", time: "6:30–7:30 pm" },
  night: { short: "Night", long: "Night", time: "late evening" },
};

export const CHANGE_LABELS: Record<SectionChangeType, { title: string; verb: string; detail: string }> = {
  close: { title: "Close for repairs", verb: "Closed", detail: "No through traffic; the rest crawl via side streets." },
  busLane: { title: "Give a lane to buses", verb: "Bus lane on", detail: "One lane fewer for cars each way." },
  addLane: { title: "Widen by one lane", verb: "Extra lane on", detail: "One more lane each way." },
  greenWave: {
    title: "More green at signals",
    verb: "Signal priority on",
    detail: "60% green instead of 50%. Crossing streets get less.",
  },
  speedLimit: { title: "Lower the speed limit to 40", verb: "40 km/h on", detail: "Calmer traffic, slower trips." },
};

export const DEVELOPMENT_LABELS: Record<DevelopmentKind, { title: string; unit: string; sizes: number[] }> = {
  housing: { title: "Housing estate", unit: "apartments", sizes: [1000, 3000, 6000] },
  office: { title: "Office cluster", unit: "employees", sizes: [2000, 5000, 10000] },
  mall: { title: "Shopping mall", unit: "m² of shops", sizes: [30000, 80000, 150000] },
};

const nf = new Intl.NumberFormat("en-US");

export function formatInt(value: number): string {
  return nf.format(Math.round(value));
}

export function formatNumber(value: number, digits = 0): string {
  return value.toLocaleString("en-US", { minimumFractionDigits: digits, maximumFractionDigits: digits });
}

export function formatSigned(value: number, digits = 1, unit = ""): string {
  const rounded = Number(value.toFixed(digits));
  if (rounded === 0) return `0${unit}`;
  const sign = rounded > 0 ? "+" : "−";
  return `${sign}${Math.abs(rounded).toLocaleString("en-US", { minimumFractionDigits: digits, maximumFractionDigits: digits })}${unit}`;
}

export function percentChange(before: number, after: number): number {
  return before === 0 ? 0 : ((after - before) / before) * 100;
}

export function sectionTitle(graph: RawCityGraph, section: number): { street: string; label: string } {
  const s = graph.sections[section];
  return { street: graph.streets[s.street].name, label: s.label };
}

export function describeChange(graph: RawCityGraph, change: Change): { title: string; detail: string } {
  if (change.type === "development") {
    const d = DEVELOPMENT_LABELS[change.kind];
    return { title: `${d.title}: ${formatInt(change.size)} ${d.unit}`, detail: `${change.lat.toFixed(4)}, ${change.lon.toFixed(4)}` };
  }
  const { street, label } = sectionTitle(graph, change.section);
  return { title: `${CHANGE_LABELS[change.type].verb} ${street}`, detail: label };
}
