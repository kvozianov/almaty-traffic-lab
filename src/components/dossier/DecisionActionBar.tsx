import ClaimBadge from "./ClaimBadge";
import { formatDecision } from "./format";
import type { ClaimInput } from "./types";

const ACTIONS = [
  {
    id: "request_more_evidence",
    label: "Запросить доказательства",
    description: "Нужны фактические скорости, надёжность автобусов, планы светофоров и оценка затрат.",
  },
  {
    id: "investigate_further",
    label: "Проверить дальше",
    description: "Устаревшее имя статуса, сохранённое только для совместимости прежних досье.",
  },
  {
    id: "defer",
    label: "Отложить",
    description: "Мера остаётся на рассмотрении, но не переходит к финансированию.",
  },
  {
    id: "fund_conditional_on_evidence",
    label: "Условное испытание",
    description: "Допустимо только после выполнения явно записанных условий по доказательствам.",
  },
  {
    id: "reject",
    label: "Отклонить",
    description: "Статус для меры, риски которой выше доказанной пользы.",
  },
  {
    id: "fund",
    label: "Финансировать сразу",
    description: "Безусловное финансирование не предусмотрено текущим контрактом досье.",
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
    (action) => action.id === currentDecision || allowedDecisions.includes(action.id) || action.id === "fund",
  );

  return (
    <section className="border-t border-stone-800 bg-stone-950 px-4 py-4" aria-label="Статусы решения">
      <div className="mx-auto flex max-w-[1400px] flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div className="min-w-0">
          <p className="font-mono text-[11px] uppercase tracking-[0.14em] text-stone-500">
            Рекомендация из опубликованного досье
          </p>
          <div className="mt-1 flex flex-wrap items-center gap-2">
            <span className="text-lg font-semibold text-stone-50">{formatDecision(currentDecision)}</span>
            <ClaimBadge level={claimLevel} />
          </div>
          <p className="mt-2 max-w-[70ch] text-xs leading-5 text-stone-500">
            Это статусы для обсуждения. Запись решения и подпись пользователя в текущей версии не реализованы.
          </p>
        </div>

        <ul className="grid min-w-0 gap-2 sm:grid-cols-2 lg:max-w-[760px] lg:grid-cols-3" aria-label="Варианты из досье">
          {visibleActions.map((action) => {
            const recorded = action.id === currentDecision;
            const allowed = allowedDecisions.includes(action.id);
            return (
              <li
                key={action.id}
                title={action.description}
                className={`min-w-0 border px-3 py-2 text-sm ${
                  recorded
                    ? "border-amber-500/55 bg-amber-500/10 text-amber-100"
                    : allowed
                      ? "border-stone-700 bg-stone-900 text-stone-300"
                      : "border-stone-800 bg-stone-950 text-stone-600"
                }`}
              >
                <span className="block break-words font-medium">{action.label}</span>
                <span className="mt-1 block font-mono text-[9px] uppercase tracking-[0.1em]">
                  {recorded ? "рекомендация" : allowed ? "допустимый статус" : "заблокировано"}
                </span>
              </li>
            );
          })}
        </ul>
      </div>
    </section>
  );
}
