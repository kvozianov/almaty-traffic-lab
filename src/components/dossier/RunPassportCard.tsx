import ClaimBadge from "./ClaimBadge";
import { commandToString, formatDateTime } from "./format";
import type { ArtifactManifestJson, ReproMetadataJson, RunPassportJson } from "./types";

function stringifyValue(value: unknown): string {
  if (value === null || value === undefined) {
    return "not provided";
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
    <section className="self-start rounded-[10px] border border-[var(--line)] bg-[var(--surface)] p-5 sm:p-6">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="font-mono text-[11px] font-medium uppercase tracking-[0.14em] text-[var(--muted)]">
            Run passport
          </p>
          <h2 className="mt-2 break-all font-mono text-base font-semibold tracking-[-0.02em] text-[var(--ink)]">
            {runPassport.runId}
          </h2>
        </div>
        <ClaimBadge level={runPassport.claimLabels?.dossier ?? reproduction?.claimLabels?.dossier ?? "proxy"} />
      </div>

      <dl className="mt-5 grid gap-x-6 gap-y-4 border-t border-[var(--line)] pt-5 text-sm sm:grid-cols-2">
        <div>
          <dt className="font-mono text-[11px] uppercase tracking-[0.12em] text-[var(--muted)]">Seed</dt>
          <dd className="mt-1 font-mono tabular-nums text-[var(--ink)]">{runPassport.seed ?? reproduction?.seed ?? "not provided"}</dd>
        </div>
        <div>
          <dt className="font-mono text-[11px] uppercase tracking-[0.12em] text-[var(--muted)]">Created</dt>
          <dd className="mt-1 font-mono tabular-nums text-[var(--ink)]">{formatDateTime(runPassport.createdAt)}</dd>
        </div>
        <div>
          <dt className="font-mono text-[11px] uppercase tracking-[0.12em] text-[var(--muted)]">Model</dt>
          <dd className="mt-1 text-[var(--ink)]">{runPassport.model?.name ?? "traffic-sim-almaty"}</dd>
        </div>
        <div>
          <dt className="font-mono text-[11px] uppercase tracking-[0.12em] text-[var(--muted)]">Version</dt>
          <dd className="mt-1 font-mono text-[var(--ink)]">{runPassport.model?.version ?? "not provided"}</dd>
        </div>
        <div className="sm:col-span-2">
          <dt className="font-mono text-[11px] uppercase tracking-[0.12em] text-[var(--muted)]">Git HEAD (incomplete record)</dt>
          <dd className="mt-1 break-all font-mono text-[var(--ink)]">
            {runPassport.model?.gitHash ?? reproduction?.sourceControl?.gitHash ?? "not provided"}
            {reproduction?.sourceControl?.dirty ? (
              <span className="ml-2 text-[var(--risk-ink)]"> uncommitted changes present</span>
            ) : (
              <span className="ml-2 text-[var(--sand-ink)]"> tracked clean-clone proof pending</span>
            )}
          </dd>
        </div>
      </dl>

      <div className="mt-5">
        <p className="font-mono text-[11px] font-medium uppercase tracking-[0.14em] text-[var(--muted)]">
          Scenario parameters
        </p>
        <div className="mt-3 divide-y divide-[var(--line)] rounded-lg border border-[var(--line)] bg-[var(--surface-raised)]">
          {scenarioEntries.map(([key, value]) => (
            <div key={key} className="grid gap-1 px-3.5 py-3 text-xs sm:grid-cols-[112px_minmax(0,1fr)] sm:gap-3">
              <div className="font-mono uppercase tracking-[0.08em] text-[var(--muted)]">{key}</div>
              <div className="min-w-0 break-all font-mono text-[var(--muted)]">{stringifyValue(value)}</div>
            </div>
          ))}
        </div>
      </div>

      <div className="mt-5">
        <p className="font-mono text-[11px] font-medium uppercase tracking-[0.14em] text-[var(--muted)]">
          Reproduce this run
        </p>
        <div className="mt-3 space-y-2 rounded-lg border border-[var(--line)] bg-[var(--canvas)] px-3.5 py-3 font-mono text-[11px] leading-5 text-[var(--muted)]">
          <p className="break-all">PYTHONPATH=src python3 scripts/reproduce_dossier.py --config simulation.config.json --out reports/repro/abay</p>
          {firstCommand ? <p className="break-all">{commandToString(firstCommand.command)}</p> : null}
          {secondCommand ? <p className="break-all">{commandToString(secondCommand.command)}</p> : null}
        </div>
      </div>

      <div className="mt-5">
        <p className="font-mono text-[11px] font-medium uppercase tracking-[0.14em] text-[var(--muted)]">
          Source snapshots
        </p>
        <div className="mt-3 max-h-[260px] overflow-auto rounded-lg border border-[var(--line)] bg-[var(--surface-raised)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--sage)]" tabIndex={0} aria-label="Scrollable source snapshots">
          {runPassport.dataSources?.map((source) => (
            <div key={source.id} className="border-b border-[var(--line)] px-3.5 py-3 last:border-b-0">
              <div className="flex items-start justify-between gap-2">
                <p className="text-sm font-medium text-[var(--ink)]">{source.label}</p>
                <ClaimBadge level={source.claim_label ?? source.claimLevel} size="xs" />
              </div>
              <p className="mt-1 break-all font-mono text-[11px] text-[var(--muted)]">{source.path}</p>
              {source.sha256 ? (
                <p className="mt-1 break-all font-mono text-[10px] text-[var(--muted)]">sha256 {source.sha256}</p>
              ) : null}
            </div>
          ))}
        </div>
      </div>

      {manifest ? (
        <div className="mt-5 border-t border-[var(--line)] pt-4 text-sm text-[var(--muted)]">
          <span className="font-mono tabular-nums text-[var(--ink)]">{manifest.artifacts.length}</span> artifacts listed in{" "}
          <span className="font-mono text-[var(--ink)]"> reports/repro/abay/artifact_manifest.json</span>.
        </div>
      ) : null}
    </section>
  );
}
