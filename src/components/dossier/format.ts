import type { ClaimInput, ClaimLevel } from "./types";

export function formatNumber(value: number, unit?: string) {
  const absolute = Math.abs(value);
  const compact = absolute >= 1_000_000;
  const formatter = new Intl.NumberFormat("ru-KZ", {
    notation: compact ? "compact" : "standard",
    maximumFractionDigits: absolute >= 100 ? 0 : 3,
  });

  if (unit?.toLowerCase().includes("kzt")) {
    return `${formatter.format(value)} ₸`;
  }

  return formatter.format(value);
}

export function formatDateTime(value?: string | null) {
  if (!value) {
    return "не указано";
  }

  const date = new Date(value);
  if (Number.isNaN(date.valueOf())) {
    return value;
  }

  return new Intl.DateTimeFormat("ru-KZ", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "UTC",
  }).format(date);
}

export function formatDecision(value: string) {
  const labels: Record<string, string> = {
    investigate_further: "проверить дальше",
    request_more_evidence: "запросить доказательства",
    defer: "отложить",
    fund_conditional_on_evidence: "условное испытание",
    reject: "отклонить",
    fund: "финансировать сразу",
  };

  return labels[value] ?? value.replaceAll("_", " ");
}

export function getClaimSortKey(level: ClaimInput) {
  const order: Record<ClaimLevel, number> = {
    demo: 1,
    proxy: 2,
    calibrated: 3,
    "real-data": 4,
    "procurement-ready": 5,
  };

  return order[(level as ClaimLevel) || "demo"] ?? 0;
}

export function commandToString(command?: string[]) {
  return command?.join(" ") ?? "не указано";
}

export function buyerSafeText(value?: string | null) {
  return (value ?? "").replaceAll("procurement-ready", "stronger");
}
