import ClaimBadge from "./ClaimBadge";
import { formatNumber } from "./format";
import type { KpiRecord } from "./types";

function deltaTone(kpi: KpiRecord) {
  if (!kpi.available) {
    return "text-stone-500";
  }

  const improved =
    kpi.direction === "higher_is_better" ? kpi.delta > 0 : kpi.delta < 0;

  if (kpi.delta === 0) {
    return "text-stone-300";
  }

  return improved ? "text-emerald-200" : "text-amber-200";
}

function formatUnit(unit: string) {
  const normalized = unit.toLowerCase();

  if (normalized.includes("person-hour")) return "чел.-ч";
  if (normalized === "km/h") return "км/ч";
  if (normalized === "percentage points") return "п.п.";
  if (normalized === "kg") return "кг";

  return unit;
}

export default function KpiDeltaTable({ kpis }: { kpis: KpiRecord[] }) {
  return (
    <section className="border-t border-stone-700/80 pt-6">
      <div className="mb-4 flex flex-col gap-2 md:flex-row md:items-end md:justify-between">
        <div>
          <p className="font-mono text-[11px] uppercase tracking-[0.14em] text-stone-500">
            Таблица изменений
          </p>
          <h2 className="mt-1 text-xl font-semibold tracking-tight text-stone-50">
            Было и стало после перенастройки светофоров
          </h2>
        </div>
        <p className="max-w-[64ch] text-sm leading-6 text-stone-400">
          Для каждого числа видны формула, единица измерения, признак чернового значения и текущий уровень доказательств.
        </p>
      </div>

      <div className="overflow-x-auto border border-stone-800">
        <table className="w-full min-w-[920px] border-collapse text-left text-sm">
          <thead className="bg-stone-950 text-[11px] uppercase tracking-[0.12em] text-stone-500">
            <tr>
              <th className="border-b border-stone-800 px-3 py-3 font-medium">Показатель</th>
              <th className="border-b border-stone-800 px-3 py-3 font-medium">Было</th>
              <th className="border-b border-stone-800 px-3 py-3 font-medium">Стало</th>
              <th className="border-b border-stone-800 px-3 py-3 font-medium">Разница</th>
              <th className="border-b border-stone-800 px-3 py-3 font-medium">Ед.</th>
              <th className="border-b border-stone-800 px-3 py-3 font-medium">Формула</th>
              <th className="border-b border-stone-800 px-3 py-3 font-medium">Статус</th>
              <th className="border-b border-stone-800 px-3 py-3 font-medium">Уровень</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-stone-800/80">
            {kpis.map((kpi) => (
              <tr key={kpi.id} className="bg-stone-950/40 align-top">
                <td className="px-3 py-3">
                  <div className="font-medium text-stone-100">{kpi.label}</div>
                  <div className="mt-1 font-mono text-[11px] text-stone-500">{kpi.id}</div>
                </td>
                <td className="px-3 py-3 font-mono text-stone-200">
                  {formatNumber(kpi.baseline, kpi.unit)}
                </td>
                <td className="px-3 py-3 font-mono text-stone-200">
                  {formatNumber(kpi.measure, kpi.unit)}
                </td>
                <td className={`px-3 py-3 font-mono font-semibold ${deltaTone(kpi)}`}>
                  {kpi.delta > 0 ? "+" : ""}
                  {formatNumber(kpi.delta, kpi.unit)}
                </td>
                <td className="px-3 py-3 font-mono text-[12px] text-stone-400">{formatUnit(kpi.unit)}</td>
                <td className="max-w-[280px] px-3 py-3 font-mono text-[11px] leading-5 text-stone-400">
                  {kpi.formula}
                </td>
                <td className="px-3 py-3">
                  <span
                    className={`inline-flex rounded-full border px-2 py-1 font-mono text-[10px] uppercase tracking-[0.08em] ${
                      kpi.placeholder
                        ? "border-amber-500/45 bg-amber-500/10 text-amber-100"
                        : "border-stone-700 bg-stone-900 text-stone-300"
                    }`}
                  >
                    {kpi.placeholder ? "черновое" : "рассчитано"}
                  </span>
                </td>
                <td className="px-3 py-3">
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
