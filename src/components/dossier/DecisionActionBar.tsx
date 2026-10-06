import ClaimBadge from "./ClaimBadge";
import { formatDecision } from "./format";
import type { ClaimInput } from "./types";

const ACTIONS = [
  {
    id: "request_more_evidence",
    label: "Request evidence",
    description: "Observed speeds, bus reliability, signal plans, and cost estimates are needed.",
  },
  {
    id: "investigate_further",
    label: "Investigate further",
    description: "A legacy status name retained only for compatibility with earlier dossiers.",
  },
  {
    id: "defer",
    label: "Defer",
    description: "The measure remains under consideration but does not proceed to funding.",
  },
  {
    id: "fund_conditional_on_evidence",
    label: "Conditional pilot",
    description: "Allowed only after explicitly recorded evidence conditions are met.",
  },
  {
    id: "reject",
    label: "Reject",
    description: "For a measure whose risks outweigh its demonstrated benefit.",
  },
];

export default function DecisionActionBar({
  currentDecision,
  allowedDecisions,
  claimLevel,
}: {
  currentDecision: string;
  allowedDecisions: string[];
  claimLevel: ClaimInput;
}) {
  const visibleActions = ACTIONS.filter(
    (action) => action.id === currentDecision || allowedDecisions.includes(action.id),
  );

  return (
    <section className="border-t border-[var(--line)] bg-[var(--surface)] px-4 py-5 sm:px-6" aria-label="Decision statuses">
      <div className="mx-auto flex max-w-[1320px] flex-col gap-5 lg:flex-row lg:items-center lg:justify-between">
        <div className="min-w-0">
          <p className="font-mono text-[11px] font-medium uppercase tracking-[0.14em] text-[var(--muted)]">
            Recommendation from the published dossier
          </p>
          <div className="mt-2 flex flex-wrap items-center gap-2">
            <span className="[font-family:var(--font-editorial)] text-xl font-semibold tracking-[-0.02em] text-[var(--ink)]">{formatDecision(currentDecision)}</span>
            <ClaimBadge level={claimLevel} />
          </div>
          <p className="mt-2 max-w-[70ch] text-xs leading-5 text-[var(--muted)]">
            These are discussion statuses. The current version does not record decisions or user signatures.
          </p>
        </div>

        <ul className="grid min-w-0 gap-2 sm:grid-cols-2 lg:max-w-[760px] lg:grid-cols-3" aria-label="Dossier options">
          {visibleActions.map((action) => {
            const recorded = action.id === currentDecision;
            const allowed = allowedDecisions.includes(action.id);
            return (
              <li
                key={action.id}
                title={action.description}
                className={`min-w-0 rounded-lg border px-3.5 py-3 text-sm ${
                  recorded
                    ? "border-[var(--line-strong)] bg-[var(--sand-wash)] text-[var(--sand-ink)]"
                    : allowed
                      ? "border-[var(--line)] bg-[var(--sage-wash)] text-[var(--sage)]"
                      : "border-[var(--line)] bg-[var(--risk-wash)] text-[var(--risk-ink)]"
                }`}
              >
                <span className="block break-words font-medium">{action.label}</span>
                <span className="mt-1 block font-mono text-[9px] uppercase tracking-[0.1em]">
                  {recorded ? "recommended" : allowed ? "allowed status" : "blocked"}
                </span>
              </li>
            );
          })}
        </ul>
      </div>
    </section>
  );
}
