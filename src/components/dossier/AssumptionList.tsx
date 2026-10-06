import ClaimBadge from "./ClaimBadge";
import type { ClaimInput } from "./types";

export default function AssumptionList({
  title,
  description,
  items,
  claimLevel,
}: {
  title: string;
  description?: string;
  items: string[];
  claimLevel?: ClaimInput;
}) {
  return (
    <section className="self-start rounded-[10px] border border-[var(--line)] bg-[var(--surface)] p-5 text-[var(--ink)] sm:p-6">
      <div className="mb-4 flex items-start justify-between gap-3">
        <div>
          <p className="font-mono text-[11px] font-medium uppercase tracking-[0.14em] text-[var(--muted)]">
            Decision evidence
          </p>
          <h2 className="mt-2 [font-family:var(--font-editorial)] text-2xl font-semibold tracking-[-0.025em] text-[var(--ink)]">{title}</h2>
        </div>
        {claimLevel ? <ClaimBadge level={claimLevel} /> : null}
      </div>
      {description ? <p className="mb-5 max-w-[68ch] text-sm leading-6 text-[var(--muted)]">{description}</p> : null}
      <ul className="divide-y divide-[var(--line)] border-y border-[var(--line)]">
        {items.map((item) => (
          <li key={item} className="px-1 py-3 text-sm leading-6 text-[var(--muted)]">
            {item}
          </li>
        ))}
      </ul>
    </section>
  );
}
