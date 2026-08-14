import ClaimBadge from "./ClaimBadge";
import { buyerSafeText, formatNumber } from "./format";
import type { ArtifactManifestJson, ProcurementJson, ReproMetadataJson, WorkflowJson } from "./types";

export default function ProcurementReadinessPanel({
  procurement,
  workflow,
  reproduction,
  manifest,
}: {
  procurement: ProcurementJson;
  workflow: WorkflowJson;
  reproduction?: ReproMetadataJson;
  manifest?: ArtifactManifestJson;
}) {
  const statusEntries = Object.entries(procurement.summary?.statuses ?? {});
  const exportLinks = [
    ...Object.entries(procurement.outputs ?? {}),
    ...Object.entries(workflow.outputs ?? {}),
  ];

  return (
    <section className="border border-stone-800 bg-stone-950/55 p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="font-mono text-[11px] uppercase tracking-[0.14em] text-stone-500">
            Готовность к закупке
          </p>
          <h2 className="mt-1 text-lg font-semibold tracking-tight text-stone-50">
            Пакет для испытания, не готовая закупка
          </h2>
        </div>
        <ClaimBadge level={procurement.claimLevel} />
      </div>

      <dl className="mt-4 grid grid-cols-3 gap-2 border-t border-stone-800 pt-4">
        <div className="border border-stone-800 px-3 py-2">
          <dt className="font-mono text-[10px] uppercase tracking-[0.12em] text-stone-500">Требования</dt>
          <dd className="mt-1 font-mono text-lg text-stone-100">
            {procurement.summary?.requirementCount ?? procurement.requirements.length}
          </dd>
        </div>
        <div className="border border-stone-800 px-3 py-2">
          <dt className="font-mono text-[10px] uppercase tracking-[0.12em] text-stone-500">Процесс</dt>
          <dd className="mt-1 font-mono text-lg text-stone-100">{workflow.status}</dd>
        </div>
        <div className="border border-stone-800 px-3 py-2">
          <dt className="font-mono text-[10px] uppercase tracking-[0.12em] text-stone-500">Список</dt>
          <dd className="mt-1 font-mono text-lg text-stone-100">
            {formatNumber(manifest?.artifacts.length ?? reproduction?.artifactCount ?? 0)}
          </dd>
        </div>
      </dl>

      {statusEntries.length > 0 ? (
        <div className="mt-4 flex flex-wrap gap-2">
          {statusEntries.map(([status, count]) => (
            <span
              key={status}
              className="rounded-full border border-stone-700 bg-stone-900 px-2.5 py-1 font-mono text-[11px] uppercase tracking-[0.08em] text-stone-300"
            >
              {status}: {count}
            </span>
          ))}
        </div>
      ) : null}

      <div className="mt-5">
        <p className="font-mono text-[11px] uppercase tracking-[0.14em] text-stone-500">
          Открытые пробелы
        </p>
        <div className="mt-2 divide-y divide-stone-800 border border-stone-800">
          {procurement.requirements.map((requirement) => (
            <div key={requirement.id} className="px-3 py-3">
              <div className="flex items-start justify-between gap-3">
                <p className="text-sm font-medium text-stone-100">{requirement.area}</p>
                <ClaimBadge level={requirement.claim_level} size="xs" />
              </div>
              <p className="mt-1 text-sm leading-6 text-stone-400">{buyerSafeText(requirement.gap)}</p>
              <p className="mt-2 font-mono text-[11px] leading-5 text-stone-500">
                {buyerSafeText(requirement.next_action)}
              </p>
            </div>
          ))}
        </div>
      </div>

      <div className="mt-5">
        <p className="font-mono text-[11px] uppercase tracking-[0.14em] text-stone-500">
          Пути к доказательствам
        </p>
        <div className="mt-2 space-y-2">
          {exportLinks.map(([label, value]) => (
            <div key={`${label}-${value}`} className="border border-stone-800 px-3 py-2">
              <p className="font-mono text-[10px] uppercase tracking-[0.12em] text-stone-500">{label}</p>
              <p className="mt-1 break-all font-mono text-[11px] text-stone-300">{value}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
