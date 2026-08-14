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
    <section className="border border-amber-500/30 bg-amber-500/[0.06] p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="font-mono text-[11px] uppercase tracking-[0.14em] text-amber-200/80">
            Проверка доказательств
          </p>
          <h2 className="mt-1 text-lg font-semibold tracking-tight text-stone-50">
            {cleanFundingAllowed ? "Безусловное финансирование разрешено" : "Безусловное финансирование заблокировано"}
          </h2>
        </div>
        <ClaimBadge level={claimLevel} />
      </div>

      <div className="mt-4 border-t border-amber-500/20 pt-4">
        <p className="text-sm leading-6 text-stone-300">
          Текущее досье можно использовать для разбора и запроса доказательств перед испытанием.
          Оно не поддерживает безусловное финансирование, пока это решение отсутствует в списке допустимых решений досье.
        </p>
      </div>

      <div className="mt-5">
        <p className="font-mono text-[11px] uppercase tracking-[0.14em] text-stone-500">
          Допустимые решения
        </p>
        <div className="mt-2 grid gap-2">
          {allowedDecisions.map((action) => (
            <div
              key={action}
              className="border border-stone-700/80 bg-stone-950/50 px-3 py-2 text-sm text-stone-200"
            >
              {formatDecision(action)}
            </div>
          ))}
        </div>
      </div>

      <div className="mt-5">
        <p className="font-mono text-[11px] uppercase tracking-[0.14em] text-stone-500">
          Что мешает более сильному уровню
        </p>
        <ul className="mt-2 space-y-2 text-sm leading-6 text-stone-300">
          {blockers.map((blocker) => (
            <li key={blocker} className="border-l border-amber-500/40 pl-3">
              {blocker}
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
