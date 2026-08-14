import type { Metadata } from "next";

import AbayCorridorMap from "@/components/dossier/AbayCorridorMap";
import AssumptionList from "@/components/dossier/AssumptionList";
import ClaimBadge from "@/components/dossier/ClaimBadge";
import DecisionActionBar from "@/components/dossier/DecisionActionBar";
import EvidenceGate from "@/components/dossier/EvidenceGate";
import KpiDeltaTable from "@/components/dossier/KpiDeltaTable";
import ProcurementReadinessPanel from "@/components/dossier/ProcurementReadinessPanel";
import RunPassportCard from "@/components/dossier/RunPassportCard";
import { formatDecision, formatNumber } from "@/components/dossier/format";
import { isEmpiricalCalibrationComplete } from "@/components/dossier/evidence";
import { loadPromotedPortfolioRelease } from "@/components/dossier/portfolioRelease";
import { normalizeClaimLevel } from "@/components/dossier/ClaimBadge";
import type {
  ApplicationPackageIndexJson,
  ArtifactManifestJson,
  DataReadinessJson,
  DossierJson,
  KpiRecord,
  PilotMonitoringPlanJson,
  ProcurementJson,
  ProcurementPackIndexJson,
  ProviderRegistryJson,
  ReproMetadataJson,
  RunPassportJson,
  SourceRecord,
  WorkflowJson,
} from "@/components/dossier/types";

export const dynamic = "force-dynamic";
export const metadata: Metadata = {
  title: "Досье сценария Абая",
  description: "Воспроизводимое proxy-досье перенастройки светофоров на проспекте Абая.",
};

type KpiRow = {
  label: string;
  before: string;
  after: string;
  delta: string;
  direction: "up" | "down" | "flat";
  tone: "positive" | "negative" | "neutral";
  claimLevel: KpiRecord["claimLevel"];
};

type EvidenceItem = {
  label: string;
  complete: boolean;
};

const HERO_KPI_IDS = [
  "person_hours_saved",
  "corridor_speed_delta",
  "bus_reliability_proxy",
  "co2_proxy",
];

const HERO_KPI_LABELS: Record<string, string> = {
  person_hours_saved: "Экономия времени",
  corridor_speed_delta: "Скорость коридора",
  bus_reliability_proxy: "Надёжность автобуса",
  co2_proxy: "Выбросы CO2",
};

function formatCalculationDate(value?: string) {
  if (!value) return "не указано";

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "не указано";

  return new Intl.DateTimeFormat("ru-KZ", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  }).format(date);
}

function hasValidDate(value?: string) {
  if (!value) return false;
  return !Number.isNaN(new Date(value).getTime());
}

function translateMeasureLabel(value: string) {
  if (value.toLowerCase().includes("signal retiming")) {
    return "Проверка перенастройки светофоров";
  }

  return value;
}

function translateRecommendation(value: string) {
  const normalized = value.toLowerCase();

  if (normalized.includes("proxy benefit appears positive")) {
    return "Предварительная польза видна, но доказательств пока недостаточно для немедленного финансирования.";
  }

  if (normalized.includes("primary proxy kpi directions are favorable")) {
    return "Направления ключевых proxy-показателей благоприятны, но уровень доказательств и оценка затрат пока не позволяют принять решение о финансировании.";
  }

  return value;
}

function translateCostNote(value: string) {
  if (value.toLowerCase().includes("placeholder until supplied by akimat or engineering estimate")) {
    return "Черновая сумма до подтверждения акиматом или инженерной оценкой.";
  }

  return value;
}

function translateCorridorName(value: string) {
  if (value === "Abay Avenue") return "проспект Абая";
  return value;
}

function translateUnit(unit: string) {
  const normalized = unit.toLowerCase();

  if (normalized.includes("person-hour")) return "чел.-ч";
  if (normalized === "km/h") return "км/ч";
  if (normalized === "percentage points") return "п.п.";
  if (normalized === "kg") return "кг";

  return unit;
}

function translateWorkflowStatus(value: string) {
  if (value === "audited") return "проверено";
  if (value === "draft") return "черновик";
  return value;
}

function normalizeKpi(kpi: KpiRecord): KpiRecord {
  return {
    ...kpi,
    available: kpi.available ?? true,
  };
}

function formatHeroValue(value: number, unit: string) {
  const unitLabel = translateUnit(unit);

  if (unit.toLowerCase().includes("kzt")) {
    return `${new Intl.NumberFormat("ru-KZ", {
      notation: "compact",
      maximumFractionDigits: 1,
    }).format(value)} ₸`;
  }

  return `${new Intl.NumberFormat("ru-KZ", {
    maximumFractionDigits: Math.abs(value) >= 100 ? 0 : 2,
  }).format(value)} ${unitLabel}`;
}

function buildHeroKpiRows(kpis: KpiRecord[]): KpiRow[] {
  return HERO_KPI_IDS.map((id) => kpis.find((kpi) => kpi.id === id))
    .filter((kpi): kpi is KpiRecord => Boolean(kpi))
    .map((kpi) => {
      const improved =
        kpi.delta === 0
          ? false
          : kpi.direction === "higher_is_better"
            ? kpi.delta > 0
            : kpi.delta < 0;

      return {
        label: HERO_KPI_LABELS[kpi.id] ?? kpi.label,
        before: formatHeroValue(kpi.baseline, kpi.unit),
        after: formatHeroValue(kpi.measure, kpi.unit),
        delta: `${kpi.delta > 0 ? "+" : ""}${formatHeroValue(kpi.delta, kpi.unit)}`,
        direction: kpi.delta === 0 ? "flat" : kpi.delta > 0 ? "up" : "down",
        tone: kpi.delta === 0 ? "neutral" : improved ? "positive" : "negative",
        claimLevel: kpi.claimLevel,
      };
    });
}

function LightClaimBadge({ level }: { level: KpiRecord["claimLevel"] }) {
  const normalized = normalizeClaimLevel(level);
  const styles = {
    demo: "border-stone-400/70 bg-stone-100 text-stone-700",
    proxy: "border-[#d9a04c]/55 bg-[#f7ead4] text-[#8a5a1c]",
    calibrated: "border-cyan-600/40 bg-cyan-50 text-cyan-800",
    "real-data": "border-emerald-600/40 bg-emerald-50 text-emerald-800",
    "procurement-ready": "border-teal-600/40 bg-teal-50 text-teal-800",
  }[normalized];

  return (
    <span className={`inline-flex h-6 items-center rounded-[6px] border px-2.5 text-[11px] font-medium uppercase tracking-[0.06em] ${styles}`}>
      {normalized}
    </span>
  );
}

function Header({ calculationDate }: { calculationDate: string }) {
  return (
    <header className="grid min-h-[52px] min-w-0 grid-cols-[minmax(0,1fr)_auto] items-center border-b border-[#ded9d0] bg-white px-4 py-2 text-[13px] text-[#6d6a62] md:grid-cols-[1fr_auto_1fr] md:px-5">
      <div className="min-w-0 truncate font-medium text-[#34322d]">Алматы · транспортная аналитика</div>
      <div className="hidden truncate px-4 text-center font-medium text-[#181814] md:block">Абай / Перенастройка светофоров</div>
      <div className="flex shrink-0 items-center justify-end gap-4">
        <span className="hidden text-[#6d6a62] sm:inline">Расчёт: {calculationDate}</span>
        <div className="grid grid-cols-2 overflow-hidden rounded-[6px] border border-[#ded9d0] text-[11px] font-medium uppercase tracking-[0.08em]">
          <span className="bg-[#181814] px-2.5 py-1 text-white">rus</span>
          <span className="px-2.5 py-1 text-[#7c776d]">қаз</span>
        </div>
      </div>
    </header>
  );
}

function DossierIntro({
  corridorName,
  lengthKm,
  intersectionCount,
  measureLabel,
  rationale,
  claimLevel,
}: {
  corridorName: string;
  lengthKm?: number;
  intersectionCount?: number;
  measureLabel: string;
  rationale: string;
  claimLevel: KpiRecord["claimLevel"];
}) {
  const corridorDetails = [
    corridorName,
    typeof lengthKm === "number" && Number.isFinite(lengthKm) ? `${lengthKm.toFixed(1)} км` : null,
    typeof intersectionCount === "number" && intersectionCount > 0
      ? `${intersectionCount} перекрёстков`
      : null,
  ].filter(Boolean);

  return (
    <section className="grid min-h-[88px] grid-cols-1 gap-4 border-b border-[#ded9d0] pb-4 xl:grid-cols-[1fr_330px]">
      <div className="min-w-0">
        <div className="mb-2 flex flex-wrap items-center gap-2">
          <h1 className="text-[22px] font-medium leading-[1.12] tracking-normal text-[#181814]">
            {measureLabel}
          </h1>
          <LightClaimBadge level={claimLevel} />
        </div>
        <p className="text-[13px] leading-5 text-[#77736a]">
          {corridorDetails.join(" · ")}
        </p>
      </div>

      <div className="border-l-4 border-[#d98b2b] bg-[#fbf5ea] px-3 py-2 text-[13px] leading-5 text-[#433b2d]">
        <span className="font-medium text-[#8a5a1c]">Рекомендация:</span> {rationale}
      </div>
    </section>
  );
}

function KpiTable({ rows }: { rows: KpiRow[] }) {
  return (
    <section className="min-h-0 flex-1 py-4">
      <div className="mb-2 hidden grid-cols-[minmax(130px,1.15fr)_minmax(118px,0.95fr)_minmax(78px,0.45fr)_72px] gap-3 px-3 text-[11px] font-medium uppercase tracking-[0.08em] text-[#8c877d] md:grid">
        <span>Показатель</span>
        <span>Было → стало</span>
        <span>Изменение</span>
        <span className="text-right">уровень</span>
      </div>
      <div className="overflow-hidden rounded-[8px] border border-[#ded9d0]">
        {rows.map((row, index) => (
          <div
            key={row.label}
            className={`grid min-w-0 grid-cols-[minmax(0,1fr)_auto] items-center gap-x-3 gap-y-2 border-b border-[#e8e3da] px-3 py-3 text-[13px] last:border-b-0 md:min-h-[66px] md:grid-cols-[minmax(130px,1.15fr)_minmax(118px,0.95fr)_minmax(78px,0.45fr)_72px] md:gap-3 md:py-0 ${
              index % 2 === 0 ? "bg-white" : "bg-[#faf9f6]"
            }`}
          >
            <div className="col-span-2 min-w-0 font-medium text-[#27241f] md:col-span-1">{row.label}</div>
            <div className="min-w-0 font-medium tabular-nums text-[#3b3933]">
              <span className="text-[#767167]">{row.before}</span>
              <span className="px-2 text-[#9a9488]">→</span>
              <span>{row.after}</span>
            </div>
            <div
              className={`flex items-center gap-1 font-medium tabular-nums ${
                row.tone === "positive"
                  ? "text-[#2f7d57]"
                  : row.tone === "negative"
                    ? "text-[#b75245]"
                    : "text-[#68645c]"
              }`}
            >
              <span>{row.delta}</span>
              {row.direction !== "flat" ? <span aria-hidden="true">{row.direction === "up" ? "↑" : "↓"}</span> : null}
            </div>
            <div className="col-span-2 flex justify-start md:col-span-1 md:justify-end">
              <LightClaimBadge level={row.claimLevel} />
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

function EvidenceGateSummary({
  items,
}: {
  items: EvidenceItem[];
}) {
  const completed = items.filter((item) => item.complete).length;
  const total = items.length;

  return (
    <div className="min-w-0 border-x border-[#ded9d0] px-4 py-3">
      <div className="mb-2 flex items-center justify-between gap-2">
        <p className="font-medium text-[#25231f]">Проверка доказательств</p>
        <p className="tabular-nums text-[#77736a]">{completed} / {total} условий</p>
      </div>
      <div className="h-1.5 overflow-hidden rounded-full bg-[#e7e2d9]">
        <div className="h-full rounded-full bg-[#2f7d57]" style={{ width: `${(completed / total) * 100}%` }} />
      </div>
      <div className="mt-2 grid grid-cols-1 gap-y-1 text-[12px] leading-4 text-[#6f6a61]">
        {items.map((item) => (
          <div key={item.label} className="flex min-w-0 items-center gap-1.5">
            <span
              className={`grid size-3.5 shrink-0 place-items-center rounded-full text-[9px] ${
                item.complete ? "bg-[#e4f0e8] text-[#2f7d57]" : "bg-[#f2e7e4] text-[#b75245]"
              }`}
            >
              {item.complete ? "✓" : "×"}
            </span>
            <span>{item.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function DecisionBar({
  currentDecision,
  allowedDecisions,
}: {
  currentDecision: string;
  allowedDecisions: string[];
}) {
  const hasCleanFund = allowedDecisions.includes("fund");

  return (
    <div className="flex min-w-0 flex-col justify-between gap-3 px-4 py-3">
      <p className="font-medium text-[#25231f]">Решение</p>
      <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 md:grid-cols-1 lg:grid-cols-2" aria-label="Сводка статуса решения">
        <div className="rounded-[7px] border border-[#d7d1c8] bg-[#f8f6f2] px-3 py-2">
          <p className="font-mono text-[9px] uppercase tracking-[0.1em] text-[#8a857b]">рекомендация</p>
          <p className="mt-1 text-[13px] font-medium leading-4 text-[#25231f]">
            {formatDecision(currentDecision)}
          </p>
        </div>
        <div className="rounded-[7px] border border-[#d7d1c8] bg-[#f8f6f2] px-3 py-2">
          <p className="font-mono text-[9px] uppercase tracking-[0.1em] text-[#8a857b]">финансирование</p>
          <p className={`mt-1 text-[13px] font-medium leading-4 ${hasCleanFund ? "text-[#2f7d57]" : "text-[#b75245]"}`}>
            {hasCleanFund ? "допустимо досье" : "заблокировано"}
          </p>
        </div>
      </div>
    </div>
  );
}

function BottomStrip({
  evidenceItems,
  capexLabel,
  costNote,
  currentDecision,
  allowedDecisions,
}: {
  evidenceItems: EvidenceItem[];
  capexLabel: string;
  costNote: string;
  currentDecision: string;
  allowedDecisions: string[];
}) {
  return (
    <section className="grid min-h-[112px] grid-cols-1 overflow-hidden rounded-[8px] border border-[#ded9d0] bg-white text-[13px] md:grid-cols-[0.82fr_1.25fr_0.93fr]">
      <div className="px-4 py-3">
        <p className="mb-2 font-medium text-[#77736a]">Оценка затрат</p>
        <p className="text-[22px] font-medium leading-none tracking-normal text-[#181814]">{capexLabel}</p>
        <p className="mt-2 text-[12px] leading-4 text-[#8a857b]">{costNote}</p>
      </div>
      <EvidenceGateSummary items={evidenceItems} />
      <DecisionBar currentDecision={currentDecision} allowedDecisions={allowedDecisions} />
    </section>
  );
}

function DataReadinessPanel({
  dataReadiness,
  providers,
  sources,
}: {
  dataReadiness: DataReadinessJson;
  providers: ProviderRegistryJson;
  sources: SourceRecord[];
}) {
  return (
    <section className="border border-stone-800 bg-stone-950/55 p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="font-mono text-[11px] uppercase tracking-[0.14em] text-stone-500">
            Готовность данных
          </p>
          <h2 className="mt-1 text-lg font-semibold tracking-tight text-stone-50">
            Что нужно запросить у города
          </h2>
        </div>
        <ClaimBadge level={dataReadiness.claimLevel} />
      </div>

      <div className="mt-4 grid grid-cols-3 gap-2 border-t border-stone-800 pt-4">
        <div className="border border-stone-800 px-3 py-2">
          <p className="font-mono text-[10px] uppercase tracking-[0.12em] text-stone-500">Источники</p>
          <p className="mt-1 font-mono text-lg text-stone-100">{providers.summary?.providerCount ?? providers.providers.length}</p>
        </div>
        <div className="border border-stone-800 px-3 py-2">
          <p className="font-mono text-[10px] uppercase tracking-[0.12em] text-stone-500">Есть</p>
          <p className="mt-1 font-mono text-lg text-stone-100">{providers.summary?.availableCount ?? 0}</p>
        </div>
        <div className="border border-stone-800 px-3 py-2">
          <p className="font-mono text-[10px] uppercase tracking-[0.12em] text-stone-500">Не хватает</p>
          <p className="mt-1 font-mono text-lg text-stone-100">{dataReadiness.missingEvidence?.length ?? 0}</p>
        </div>
      </div>

      <div className="mt-5">
        <p className="font-mono text-[11px] uppercase tracking-[0.14em] text-stone-500">
          Запрошенные наборы данных
        </p>
        <div className="mt-2 divide-y divide-stone-800 border border-stone-800">
          {dataReadiness.akimatRequests?.map((request) => (
            <div key={request.id} className="px-3 py-3">
              <div className="flex items-start justify-between gap-3">
                <p className="text-sm font-medium text-stone-100">{request.dataset}</p>
                <ClaimBadge level={request.current_claim_level} size="xs" />
              </div>
              <p className="mt-1 text-sm leading-6 text-stone-400">{request.why_needed}</p>
              <p className="mt-2 font-mono text-[11px] leading-5 text-stone-500">{request.minimum_format}</p>
            </div>
          ))}
        </div>
      </div>

      <div className="mt-5">
        <p className="font-mono text-[11px] uppercase tracking-[0.14em] text-stone-500">
          Источники досье
        </p>
        <div className="mt-2 grid gap-2">
          {sources.map((source) => (
            <div key={source.id} className="border border-stone-800 px-3 py-2">
              <div className="flex items-start justify-between gap-3">
                <p className="text-sm font-medium text-stone-100">{source.label}</p>
                <ClaimBadge level={source.claim_label ?? source.claimLevel} size="xs" />
              </div>
              <p className="mt-1 break-all font-mono text-[11px] text-stone-500">{source.path ?? source.provider ?? source.source_type}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function WorkflowCustodyPanel({ workflow }: { workflow: WorkflowJson }) {
  return (
    <section className="border border-stone-800 bg-stone-950/55 p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="font-mono text-[11px] uppercase tracking-[0.14em] text-stone-500">
            Цепочка проверки
          </p>
          <h2 className="mt-1 text-lg font-semibold tracking-tight text-stone-50">
            {translateWorkflowStatus(workflow.status)}: {workflow.currentOwner}
          </h2>
        </div>
        <ClaimBadge level={workflow.claimLevel} />
      </div>

      <div className="mt-4 grid grid-cols-3 gap-2 border-t border-stone-800 pt-4">
        <div className="border border-stone-800 px-3 py-2">
          <p className="font-mono text-[10px] uppercase tracking-[0.12em] text-stone-500">История</p>
          <p className="mt-1 font-mono text-lg text-stone-100">{workflow.history.length}</p>
        </div>
        <div className="border border-stone-800 px-3 py-2">
          <p className="font-mono text-[10px] uppercase tracking-[0.12em] text-stone-500">Слепки</p>
          <p className="mt-1 font-mono text-lg text-stone-100">{workflow.artifactLocks.length}</p>
        </div>
        <div className="border border-stone-800 px-3 py-2">
          <p className="font-mono text-[10px] uppercase tracking-[0.12em] text-stone-500">Готово</p>
          <p className="mt-1 font-mono text-lg text-stone-100">
            {workflow.evidenceCompleteness?.satisfiedEvidenceCount ?? 0}
          </p>
        </div>
      </div>

      <div className="mt-5">
        <p className="font-mono text-[11px] uppercase tracking-[0.14em] text-stone-500">
          Слепки артефактов
        </p>
        <div className="mt-2 divide-y divide-stone-800 border border-stone-800">
          {workflow.artifactLocks.map((lock) => (
            <div key={lock.path} className="px-3 py-3">
              <div className="flex items-start justify-between gap-3">
                <p className="break-all font-mono text-[11px] text-stone-300">{lock.path}</p>
                <span className={`font-mono text-[10px] uppercase ${lock.available ? "text-emerald-200" : "text-amber-200"}`}>
                  {lock.available ? "есть" : "нет"}
                </span>
              </div>
              {lock.sha256 ? <p className="mt-1 break-all font-mono text-[10px] text-stone-600">sha256 {lock.sha256}</p> : null}
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function ExportPackPanel({
  dossier,
  procurementPack,
  applicationPack,
  pilotPlan,
}: {
  dossier: DossierJson;
  procurementPack: ProcurementPackIndexJson;
  applicationPack: ApplicationPackageIndexJson;
  pilotPlan: PilotMonitoringPlanJson;
}) {
  const dossierOutputs = Object.entries(dossier.outputs ?? {});
  const packOutputs = procurementPack.outputs;

  return (
    <section className="border-t border-stone-700/80 pt-6">
      <div className="mb-4 flex flex-col gap-2 md:flex-row md:items-end md:justify-between">
        <div>
          <p className="font-mono text-[11px] uppercase tracking-[0.14em] text-stone-500">
            Выгрузки и доказательства для испытания
          </p>
          <h2 className="mt-1 text-xl font-semibold tracking-tight text-stone-50">
            Текущий пакет подходит для проверки испытания
          </h2>
        </div>
        <div className="flex flex-wrap gap-2">
          <ClaimBadge level={procurementPack.claimLevel} />
          <ClaimBadge level={dossier.claimLevel} />
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <div className="border border-stone-800 bg-stone-950/55 p-4">
          <p className="font-mono text-[11px] uppercase tracking-[0.14em] text-stone-500">Файлы досье</p>
          <div className="mt-3 space-y-2">
            {dossierOutputs.map(([label, value]) => (
              <div key={label} className="border border-stone-800 px-3 py-2">
                <p className="font-mono text-[10px] uppercase tracking-[0.12em] text-stone-500">{label}</p>
                <p className="mt-1 break-all font-mono text-[11px] text-stone-300">{value}</p>
              </div>
            ))}
          </div>
        </div>

        <div className="border border-stone-800 bg-stone-950/55 p-4">
          <p className="font-mono text-[11px] uppercase tracking-[0.14em] text-stone-500">Пакет для акимата</p>
          <div className="mt-3 space-y-2">
            {packOutputs.map((output) => (
              <div key={`${output.role}-${output.path}`} className="border border-stone-800 px-3 py-2">
                <p className="font-mono text-[10px] uppercase tracking-[0.12em] text-stone-500">{output.role}</p>
                <p className="mt-1 break-all font-mono text-[11px] text-stone-300">{output.path}</p>
              </div>
            ))}
          </div>
        </div>

        <div className="border border-stone-800 bg-stone-950/55 p-4">
          <p className="font-mono text-[11px] uppercase tracking-[0.14em] text-stone-500">Как понять успех испытания</p>
          <h3 className="mt-1 text-base font-semibold text-stone-50">{applicationPack.nextAction}</h3>
          <div className="mt-3 space-y-2">
            {pilotPlan.criteria.map((criterion) => (
              <div key={criterion.id} className="border-l border-amber-500/40 pl-3 text-sm leading-6 text-stone-300">
                {criterion.kpi_id}: {criterion.acceptable_threshold}
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

export default async function AbaySignalRetimingDossierPage() {
  const release = await loadPromotedPortfolioRelease();
  const roadsSource = release.sources.roadsGeojson;
  if (!roadsSource) {
    throw new Error("The promoted release is missing its immutable roadsGeojson source.");
  }
  const dossier = release.artifacts.dossier as DossierJson;
  const runPassport = release.artifacts.runPassport as RunPassportJson;
  const providers = release.artifacts.providers as ProviderRegistryJson;
  const workflow = release.artifacts.workflow as WorkflowJson;
  const procurement = release.artifacts.procurement as ProcurementJson;
  const reproduction = release.artifacts.reproduction as ReproMetadataJson;
  const manifest = release.artifacts.manifest as ArtifactManifestJson;
  const dataReadiness = release.artifacts.dataReadiness as DataReadinessJson;
  const procurementPack = release.artifacts.procurementPack as ProcurementPackIndexJson;
  const applicationPack = release.artifacts.applicationPack as ApplicationPackageIndexJson;
  const pilotPlan = release.artifacts.pilotPlan as PilotMonitoringPlanJson;

  const normalizedKpis = dossier.executiveKpis.kpis.map(normalizeKpi);
  const heroKpiRows = buildHeroKpiRows(normalizedKpis);
  const corridorName = translateCorridorName(dossier.corridor?.name ?? "проспект Абая");
  const lengthKm = dossier.corridor.lengthKm;
  const intersectionCount =
    dossier.corridor.intersectionCount ?? runPassport.calibrationValidation?.intersectionCount;
  const calculationDate = formatCalculationDate(runPassport.createdAt);
  const capexLabel = dossier.capexOpex ? formatNumber(dossier.capexOpex.capexKzt, "KZT") : "не указано";
  const roadsProvider = providers.providers.find((provider) => provider.id === "roads-geojson");
  const scenarioConfigSource = dossier.sources.find((source) =>
    `${source.id} ${source.path ?? ""}`.toLowerCase().includes("scenario"),
  );
  const observedDataAvailable = providers.providers.some(
    (provider) =>
      provider.id !== "roads-geojson" &&
      provider.available === true &&
      normalizeClaimLevel(provider.claim_label ?? provider.claimLevel) === "real-data",
  );
  const costKpis = normalizedKpis.filter((kpi) =>
    ["capex_placeholder", "opex_placeholder"].includes(kpi.id),
  );
  const evidenceItems: EvidenceItem[] = [
    { label: "геометрия дорог", complete: roadsProvider?.available === true },
    { label: "конфиг сценария", complete: Boolean(scenarioConfigSource) },
    { label: "паспорт запуска", complete: Boolean(runPassport.runId) },
    { label: "дата расчёта", complete: hasValidDate(runPassport.createdAt) },
    { label: "наблюдаемые данные", complete: observedDataAvailable },
    {
      label: "эмпирическая валидация",
      complete: isEmpiricalCalibrationComplete(runPassport.calibrationValidation),
    },
    {
      label: "оценка стоимости",
      complete: costKpis.length === 2 && costKpis.every((kpi) => kpi.available && !kpi.placeholder),
    },
  ];

  return (
    <main className="min-h-[100dvh] min-w-0 overflow-x-clip bg-[#f4f3ef] text-[#181814]" style={{ colorScheme: "light" }}>
      <Header calculationDate={calculationDate} />

      <div className="grid min-w-0 grid-cols-1 lg:min-h-[calc(100dvh-52px)] lg:grid-cols-[38%_62%]">
        <section className="order-2 h-[360px] min-w-0 border-b border-[#ded9d0] bg-[#11110f] sm:h-[420px] lg:order-1 lg:h-auto lg:border-b-0">
          <AbayCorridorMap
            runId={release.manifest.runId}
            expectedSourceSha256={roadsSource.sha256}
            evidence={{
              available: roadsProvider?.available === true,
              claimLevel: normalizeClaimLevel(roadsProvider?.claim_label ?? roadsProvider?.claimLevel),
              freshness: roadsProvider?.freshness,
            }}
          />
        </section>

        <section className="order-1 flex min-h-0 min-w-0 flex-col bg-white px-4 py-5 sm:px-5 lg:order-2 lg:border-l lg:border-[#ded9d0] xl:px-6">
          <DossierIntro
            corridorName={corridorName}
            lengthKm={lengthKm}
            intersectionCount={intersectionCount}
            measureLabel={translateMeasureLabel(dossier.proposedMeasure.label)}
            rationale={translateRecommendation(dossier.recommendation.rationale)}
            claimLevel={dossier.claimLevel}
          />
          <KpiTable rows={heroKpiRows} />
          <BottomStrip
            evidenceItems={evidenceItems}
            capexLabel={capexLabel}
            costNote={
              dossier.capexOpex
                ? translateCostNote(dossier.capexOpex.notes)
                : "Источник оценки не указан в досье."
            }
            currentDecision={dossier.recommendation.decision}
            allowedDecisions={dossier.recommendation.allowedDecisions}
          />
        </section>
      </div>

      <section className="min-w-0 bg-[#0f0f0d] px-4 py-8 text-stone-100 sm:px-5">
        <div className="mx-auto flex max-w-[1440px] flex-col gap-8">
          <header className="grid gap-4 border-b border-stone-800 pb-6 lg:grid-cols-[minmax(0,1fr)_auto] lg:items-end">
            <div>
              <p className="font-mono text-[11px] uppercase tracking-[0.14em] text-stone-500">
                Аудит досье
              </p>
              <h2 className="mt-2 text-2xl font-semibold tracking-tight text-stone-50">
                Рабочий экран решения
              </h2>
              <p className="mt-2 max-w-[82ch] text-sm leading-6 text-stone-400">
                Верхний экран опирается на полную цепочку доказательств по Абаю: файл показателей JSON,
                паспорт запуска, ограничения источников, цепочку проверки, пробелы для закупки и пути выгрузки.
                {dossier.recommendation.allowedDecisions.includes("fund")
                  ? " Досье содержит статус финансирования, который всё равно требует отдельной записи решения."
                  : " Безусловное финансирование не входит в допустимые статусы этого досье."}
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              <span
                className="max-w-full break-all rounded-full border border-stone-700 px-2.5 py-1 font-mono text-[10px] uppercase tracking-[0.08em] text-stone-400"
                title={`Релиз ${release.manifest.runId}`}
              >
                неизменяемый релиз · aliases {release.manifest.aliases.status}
              </span>
              <ClaimBadge level={dossier.claimLevel} />
              <ClaimBadge level={workflow.claimLevel} />
              <ClaimBadge level={procurement.claimLevel} />
            </div>
          </header>

          <div className="grid gap-5 xl:grid-cols-[minmax(0,0.95fr)_minmax(420px,1.05fr)]">
            <EvidenceGate
              currentClaimLevel={dossier.claimLevel}
              allowedDecisions={dossier.recommendation.allowedDecisions}
              risks={dossier.risks}
              limitations={dossier.limitations}
            />
            <RunPassportCard runPassport={runPassport} reproduction={reproduction} manifest={manifest} />
          </div>

          <KpiDeltaTable kpis={normalizedKpis} />

          <div className="grid gap-5 xl:grid-cols-2">
            <AssumptionList
              title="Допущения, ограничения и риски"
              description="Это причины, по которым досье пока остаётся файлом решения уровня proxy."
              items={[...dossier.assumptions, ...dossier.limitations, ...dossier.risks]}
              claimLevel={dossier.claimLevel}
            />
            <DataReadinessPanel
              dataReadiness={dataReadiness}
              providers={providers}
              sources={dossier.sources}
            />
          </div>

          <div className="grid gap-5 xl:grid-cols-[minmax(0,0.95fr)_minmax(420px,1.05fr)]">
            <WorkflowCustodyPanel workflow={workflow} />
            <ProcurementReadinessPanel
              procurement={procurement}
              workflow={workflow}
              reproduction={reproduction}
              manifest={manifest}
            />
          </div>

          <ExportPackPanel
            dossier={dossier}
            procurementPack={procurementPack}
            applicationPack={applicationPack}
            pilotPlan={pilotPlan}
          />
        </div>
      </section>

      <DecisionActionBar
        currentDecision={dossier.recommendation.decision}
        allowedDecisions={dossier.recommendation.allowedDecisions}
        claimLevel={dossier.claimLevel}
      />
    </main>
  );
}
