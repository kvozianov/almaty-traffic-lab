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
    <section className="border-t border-stone-700/80 pt-6">
      <div className="mb-3 flex items-start justify-between gap-3">
        <div>
          <p className="font-mono text-[11px] uppercase tracking-[0.14em] text-stone-500">
            Доказательства решения
          </p>
          <h2 className="mt-1 text-xl font-semibold tracking-tight text-stone-50">{title}</h2>
        </div>
        {claimLevel ? <ClaimBadge level={claimLevel} /> : null}
      </div>
      {description ? <p className="mb-4 max-w-[68ch] text-sm leading-6 text-stone-400">{description}</p> : null}
      <div className="grid gap-2">
        {items.map((item) => (
          <div key={item} className="border-l border-stone-700 bg-stone-950/35 px-3 py-2 text-sm leading-6 text-stone-300">
            {item}
          </div>
        ))}
      </div>
    </section>
  );
}
