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
    <section className="self-start rounded-[10px] border border-[var(--line)] bg-[var(--surface)] p-5 sm:p-6">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="font-mono text-[11px] font-medium uppercase tracking-[0.14em] text-[var(--muted)]">
            Procurement readiness
          </p>
          <h2 className="mt-2 [font-family:var(--font-editorial)] text-xl font-semibold tracking-[-0.025em] text-[var(--ink)]">
            Pilot package, not procurement-ready
          </h2>
        </div>
        <ClaimBadge level={procurement.claimLevel} />
      </div>

      <dl className="mt-5 grid gap-2 border-t border-[var(--line)] pt-5 sm:grid-cols-3">
        <div className="rounded-lg border border-[var(--line)] bg-[var(--surface-raised)] px-3.5 py-3">
          <dt className="font-mono text-[10px] uppercase tracking-[0.12em] text-[var(--muted)]">Requirements</dt>
          <dd className="mt-1 font-mono text-lg tabular-nums text-[var(--ink)]">
            {procurement.summary?.requirementCount ?? procurement.requirements.length}
          </dd>
        </div>
        <div className="rounded-lg border border-[var(--line)] bg-[var(--surface-raised)] px-3.5 py-3">
          <dt className="font-mono text-[10px] uppercase tracking-[0.12em] text-[var(--muted)]">Workflow</dt>
          <dd className="mt-1 break-words font-mono text-base text-[var(--ink)]">{workflow.status}</dd>
        </div>
        <div className="rounded-lg border border-[var(--line)] bg-[var(--surface-raised)] px-3.5 py-3">
          <dt className="font-mono text-[10px] uppercase tracking-[0.12em] text-[var(--muted)]">Manifest</dt>
          <dd className="mt-1 font-mono text-lg tabular-nums text-[var(--ink)]">
            {formatNumber(manifest?.artifacts.length ?? reproduction?.artifactCount ?? 0)}
          </dd>
        </div>
      </dl>

      {statusEntries.length > 0 ? (
        <div className="mt-4 flex flex-wrap gap-2">
          {statusEntries.map(([status, count]) => (
            <span
              key={status}
              className="rounded-full border border-[var(--line-strong)] bg-[var(--sand-wash)] px-2.5 py-1 font-mono text-[11px] uppercase tracking-[0.08em] text-[var(--sand-ink)]"
            >
              {status}: {count}
            </span>
          ))}
        </div>
      ) : null}

      <div className="mt-5">
        <p className="font-mono text-[11px] font-medium uppercase tracking-[0.14em] text-[var(--muted)]">
          Open gaps
        </p>
        <div className="mt-3 divide-y divide-[var(--line)] rounded-lg border border-[var(--line)] bg-[var(--risk-wash)]">
          {procurement.requirements.map((requirement) => (
            <div key={requirement.id} className="px-3.5 py-3.5">
              <div className="flex items-start justify-between gap-3">
                <p className="text-sm font-medium text-[var(--ink)]">{requirement.area}</p>
                <ClaimBadge level={requirement.claim_level} size="xs" />
              </div>
              <p className="mt-1 text-sm leading-6 text-[var(--muted)]">{buyerSafeText(requirement.gap)}</p>
              <p className="mt-2 font-mono text-[11px] leading-5 text-[var(--risk-ink)]">
                {buyerSafeText(requirement.next_action)}
              </p>
            </div>
          ))}
        </div>
      </div>

      <div className="mt-5">
        <p className="font-mono text-[11px] font-medium uppercase tracking-[0.14em] text-[var(--muted)]">
          Evidence paths
        </p>
        <div className="mt-3 space-y-2">
          {exportLinks.map(([label, value]) => (
            <div key={`${label}-${value}`} className="rounded-lg border border-[var(--line)] bg-[var(--surface-raised)] px-3.5 py-3">
              <p className="font-mono text-[10px] uppercase tracking-[0.12em] text-[var(--muted)]">{label}</p>
              <p className="mt-1 break-all font-mono text-[11px] text-[var(--muted)]">{value}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
