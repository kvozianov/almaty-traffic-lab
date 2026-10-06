import ClaimBadge, { normalizeClaimLevel } from "./ClaimBadge";
import { formatDecision } from "./format";
import type { ClaimInput } from "./types";

export default function EvidenceGate({
  currentClaimLevel,
  allowedDecisions,
  risks,
  limitations,
}: {
  currentClaimLevel: ClaimInput;
  allowedDecisions: string[];
  risks: string[];
  limitations: string[];
}) {
  const claimLevel = normalizeClaimLevel(currentClaimLevel);
  const blockers = [...risks, ...limitations];
  const cleanFundingAllowed =
    allowedDecisions.includes("fund") && claimLevel === "procurement-ready" && blockers.length === 0;

  return (
    <section
      className={`self-start rounded-[10px] border border-[var(--line)] p-5 sm:p-6 ${
        cleanFundingAllowed ? "bg-[var(--sage-wash)]" : "bg-[var(--risk-wash)]"
      }`}
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <p
            className={`font-mono text-[11px] font-medium uppercase tracking-[0.14em] ${
              cleanFundingAllowed ? "text-[var(--sage)]" : "text-[var(--risk-ink)]"
            }`}
          >
            Evidence gate
          </p>
          <h2 className="mt-2 [font-family:var(--font-editorial)] text-xl font-semibold tracking-[-0.025em] text-[var(--ink)]">
            {cleanFundingAllowed ? "Unconditional funding allowed" : "Unconditional funding blocked"}
          </h2>
        </div>
        <ClaimBadge level={claimLevel} />
      </div>

      <div className="mt-5 border-t border-[var(--line)] pt-4">
        <p className="max-w-[68ch] text-sm leading-6 text-[var(--muted)]">
          This dossier can support review and evidence requests before a pilot.
          It does not support unconditional funding while that decision is absent from the dossier&apos;s allowed decisions.
        </p>
      </div>

      <div className="mt-6">
        <p className="font-mono text-[11px] font-medium uppercase tracking-[0.14em] text-[var(--muted)]">
          Allowed decisions
        </p>
        <div className="mt-3 grid gap-2 sm:grid-cols-2">
          {allowedDecisions.map((action) => (
            <div
              key={action}
              className="rounded-lg border border-[var(--line)] bg-[var(--surface-raised)] px-3.5 py-3 text-sm font-medium text-[var(--ink)]"
            >
              {formatDecision(action)}
            </div>
          ))}
        </div>
      </div>

      <div className="mt-5">
        <p className="font-mono text-[11px] font-medium uppercase tracking-[0.14em] text-[var(--muted)]">
          What blocks a stronger claim level
        </p>
        <ul className="mt-3 divide-y divide-[var(--line)] border-y border-[var(--line)] text-sm leading-6 text-[var(--muted)]">
          {blockers.map((blocker) => (
            <li key={blocker} className="py-3 pl-3 before:mr-3 before:text-[var(--risk-ink)] before:content-['—']">
              {blocker}
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
