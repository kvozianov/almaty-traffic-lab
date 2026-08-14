import ClaimBadge from "./ClaimBadge";
import { commandToString, formatDateTime } from "./format";
import type { ArtifactManifestJson, ReproMetadataJson, RunPassportJson } from "./types";

function stringifyValue(value: unknown): string {
  if (value === null || value === undefined) {
    return "не указано";
  }

  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }

  return JSON.stringify(value);
}

export default function RunPassportCard({
  runPassport,
  reproduction,
  manifest,
}: {
  runPassport: RunPassportJson;
  reproduction?: ReproMetadataJson;
  manifest?: ArtifactManifestJson;
}) {
  const scenarioEntries = Object.entries(runPassport.scenarioParams ?? {});
  const firstCommand = reproduction?.commands?.[0];
  const secondCommand = reproduction?.commands?.[1];

  return (
    <section className="border border-stone-800 bg-stone-950/55 p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="font-mono text-[11px] uppercase tracking-[0.14em] text-stone-500">
            Паспорт запуска
          </p>
          <h2 className="mt-1 text-lg font-semibold tracking-tight text-stone-50">
            {runPassport.runId}
          </h2>
        </div>
        <ClaimBadge level={runPassport.claimLabels?.dossier ?? reproduction?.claimLabels?.dossier ?? "proxy"} />
      </div>

      <dl className="mt-4 grid grid-cols-2 gap-3 border-t border-stone-800 pt-4 text-sm">
        <div>
          <dt className="font-mono text-[11px] uppercase tracking-[0.12em] text-stone-500">Зерно</dt>
          <dd className="mt-1 font-mono text-stone-100">{runPassport.seed ?? reproduction?.seed ?? "не указано"}</dd>
        </div>
        <div>
          <dt className="font-mono text-[11px] uppercase tracking-[0.12em] text-stone-500">Создано</dt>
          <dd className="mt-1 font-mono text-stone-100">{formatDateTime(runPassport.createdAt)}</dd>
        </div>
        <div>
          <dt className="font-mono text-[11px] uppercase tracking-[0.12em] text-stone-500">Модель</dt>
          <dd className="mt-1 text-stone-100">{runPassport.model?.name ?? "traffic-sim-almaty"}</dd>
        </div>
        <div>
          <dt className="font-mono text-[11px] uppercase tracking-[0.12em] text-stone-500">Версия</dt>
          <dd className="mt-1 font-mono text-stone-100">{runPassport.model?.version ?? "не указано"}</dd>
        </div>
        <div className="col-span-2">
          <dt className="font-mono text-[11px] uppercase tracking-[0.12em] text-stone-500">Git HEAD (неполная фиксация)</dt>
          <dd className="mt-1 font-mono text-stone-100">
            {runPassport.model?.gitHash ?? reproduction?.sourceControl?.gitHash ?? "не указано"}
            {reproduction?.sourceControl?.dirty ? (
              <span className="ml-2 text-amber-200"> есть незакоммиченные изменения</span>
            ) : (
              <span className="ml-2 text-amber-200"> tracked clean-clone proof pending</span>
            )}
          </dd>
        </div>
      </dl>

      <div className="mt-5">
        <p className="font-mono text-[11px] uppercase tracking-[0.14em] text-stone-500">
          Параметры сценария
        </p>
        <div className="mt-2 divide-y divide-stone-800 border border-stone-800">
          {scenarioEntries.map(([key, value]) => (
            <div key={key} className="grid grid-cols-[112px_minmax(0,1fr)] gap-3 px-3 py-2 text-xs">
              <div className="font-mono uppercase tracking-[0.08em] text-stone-500">{key}</div>
              <div className="min-w-0 break-all font-mono text-stone-300">{stringifyValue(value)}</div>
            </div>
          ))}
        </div>
      </div>

      <div className="mt-5">
        <p className="font-mono text-[11px] uppercase tracking-[0.14em] text-stone-500">
          Как повторить расчёт
        </p>
        <div className="mt-2 space-y-2 border border-stone-800 bg-stone-950 px-3 py-3 font-mono text-[11px] leading-5 text-stone-300">
          <p>PYTHONPATH=src python3 scripts/reproduce_dossier.py --config simulation.config.json --out reports/repro/abay</p>
          {firstCommand ? <p>{commandToString(firstCommand.command)}</p> : null}
          {secondCommand ? <p>{commandToString(secondCommand.command)}</p> : null}
        </div>
      </div>

      <div className="mt-5">
        <p className="font-mono text-[11px] uppercase tracking-[0.14em] text-stone-500">
          Слепки источников
        </p>
        <div className="mt-2 max-h-[260px] overflow-auto border border-stone-800">
          {runPassport.dataSources?.map((source) => (
            <div key={source.id} className="border-b border-stone-800 px-3 py-3 last:border-b-0">
              <div className="flex items-start justify-between gap-2">
                <p className="text-sm font-medium text-stone-100">{source.label}</p>
                <ClaimBadge level={source.claim_label ?? source.claimLevel} size="xs" />
              </div>
              <p className="mt-1 font-mono text-[11px] text-stone-500">{source.path}</p>
              {source.sha256 ? (
                <p className="mt-1 break-all font-mono text-[10px] text-stone-600">sha256 {source.sha256}</p>
              ) : null}
            </div>
          ))}
        </div>
      </div>

      {manifest ? (
        <div className="mt-5 border-t border-stone-800 pt-4 text-sm text-stone-300">
          <span className="font-mono text-stone-500">{manifest.artifacts.length}</span> артефакт в списке{" "}
          <span className="font-mono text-stone-200"> reports/repro/abay/artifact_manifest.json</span>.
        </div>
      ) : null}
    </section>
  );
}
