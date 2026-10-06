import ClaimBadge from "./ClaimBadge";
import { formatNumber } from "./format";
import type { KpiRecord } from "./types";

function deltaTone(kpi: KpiRecord) {
  if (!kpi.available) {
    return "text-[var(--muted)]";
  }

  const improved =
    kpi.direction === "higher_is_better" ? kpi.delta > 0 : kpi.delta < 0;

  if (kpi.delta === 0) {
    return "text-[var(--muted)]";
  }

  return improved ? "text-[var(--sage)]" : "text-[var(--risk-ink)]";
}

function formatUnit(unit: string) {
  const normalized = unit.toLowerCase();

  if (normalized.includes("person-hour")) return "person-hours";
  if (normalized === "km/h") return "km/h";
  if (normalized === "percentage points") return "pp";
  if (normalized === "kg") return "kg";

  return unit;
}

export default function KpiDeltaTable({ kpis }: { kpis: KpiRecord[] }) {
  return (
    <section className="rounded-[10px] border border-[var(--line)] bg-[var(--surface)] p-5 text-[var(--ink)] sm:p-6">
      <div className="mb-5 flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div>
          <p className="font-mono text-[11px] font-medium uppercase tracking-[0.14em] text-[var(--muted)]">
            Delta table
          </p>
          <h2 id="kpi-delta-table-title" className="mt-2 [font-family:var(--font-editorial)] text-2xl font-semibold tracking-[-0.025em] text-[var(--ink)]">
            Before and after signal retiming
          </h2>
        </div>
        <p className="max-w-[60ch] text-sm leading-6 text-[var(--muted)]">
          Each value includes its formula, unit, placeholder status, and current claim level.
        </p>
      </div>

      <div
        className="overflow-x-auto rounded-[10px] border border-[var(--line)] bg-[var(--surface)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--sage)]"
        role="region"
        aria-labelledby="kpi-delta-table-title"
        tabIndex={0}
      >
        <table className="w-full min-w-[920px] border-collapse text-left text-sm text-[var(--ink)]">
          <caption className="sr-only">Before-and-after proxy KPI values for the Abay Avenue signal-retiming case.</caption>
          <thead className="bg-[var(--canvas)] font-mono text-[11px] uppercase tracking-[0.12em] text-[var(--muted)]">
            <tr>
              <th className="border-b border-[var(--line)] px-4 py-3 font-medium">Metric</th>
              <th className="border-b border-[var(--line)] px-4 py-3 font-medium">Baseline</th>
              <th className="border-b border-[var(--line)] px-4 py-3 font-medium">Measure</th>
              <th className="border-b border-[var(--line)] px-4 py-3 font-medium">Delta</th>
              <th className="border-b border-[var(--line)] px-4 py-3 font-medium">Unit</th>
              <th className="border-b border-[var(--line)] px-4 py-3 font-medium">Formula</th>
              <th className="border-b border-[var(--line)] px-4 py-3 font-medium">Status</th>
              <th className="border-b border-[var(--line)] px-4 py-3 font-medium">Level</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[var(--line)]">
            {kpis.map((kpi) => (
              <tr key={kpi.id} className="bg-[var(--surface)] align-top transition-colors hover:bg-[var(--canvas)]">
                <td className="px-4 py-4">
                  <div className="font-medium text-[var(--ink)]">{kpi.label}</div>
                  <div className="mt-1 font-mono text-[11px] text-[var(--muted)]">{kpi.id}</div>
                </td>
                <td className="px-4 py-4 font-mono tabular-nums text-[var(--ink)]">
                  {formatNumber(kpi.baseline, kpi.unit)}
                </td>
                <td className="px-4 py-4 font-mono tabular-nums text-[var(--ink)]">
                  {formatNumber(kpi.measure, kpi.unit)}
                </td>
                <td className={`px-4 py-4 font-mono font-semibold tabular-nums ${deltaTone(kpi)}`}>
                  {kpi.delta > 0 ? "+" : ""}
                  {formatNumber(kpi.delta, kpi.unit)}
                </td>
                <td className="px-4 py-4 font-mono text-[12px] text-[var(--muted)]">{formatUnit(kpi.unit)}</td>
                <td className="max-w-[280px] px-4 py-4 font-mono text-[11px] leading-5 text-[var(--muted)]">
                  {kpi.formula}
                </td>
                <td className="px-4 py-4">
                  <span
                    className={`inline-flex rounded-full border px-2 py-1 font-mono text-[10px] uppercase tracking-[0.08em] ${
                      kpi.placeholder
                        ? "border-[var(--line-strong)] bg-[var(--sand-wash)] text-[var(--sand-ink)]"
                        : "border-[var(--line)] bg-[var(--sage-wash)] text-[var(--sage)]"
                    }`}
                  >
                    {kpi.placeholder ? "placeholder" : "calculated"}
                  </span>
                </td>
                <td className="px-4 py-4">
                  <ClaimBadge level={kpi.claimLevel} size="xs" />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
