import type { ClaimInput, ClaimLevel } from "./types";

const CLAIM_LEVELS: ClaimLevel[] = [
  "demo",
  "proxy",
  "calibrated",
  "real-data",
  "procurement-ready",
];

const CLAIM_STYLES: Record<ClaimLevel, string> = {
  demo: "border-[var(--line-strong)] bg-[var(--canvas)] text-[var(--muted)]",
  proxy: "border-[var(--line-strong)] bg-[var(--sand-wash)] text-[var(--sand-ink)]",
  calibrated: "border-[var(--line-strong)] bg-[var(--sage-wash)] text-[var(--sage)]",
  "real-data": "border-[var(--line-strong)] bg-[var(--sage-wash)] text-[var(--sage)]",
  "procurement-ready": "border-[var(--sage)] bg-[var(--sage)] text-[var(--surface-raised)]",
};

export function normalizeClaimLevel(claimLevel: ClaimInput): ClaimLevel {
  if (typeof claimLevel === "string" && CLAIM_LEVELS.includes(claimLevel as ClaimLevel)) {
    return claimLevel as ClaimLevel;
  }

  return "demo";
}

export default function ClaimBadge({
  level,
  size = "sm",
}: {
  level: ClaimInput;
  size?: "xs" | "sm";
}) {
  const normalized = normalizeClaimLevel(level);
  const sizeClass = size === "xs" ? "px-2 py-0.5 text-[10px]" : "px-2.5 py-1 text-[11px]";

  return (
    <span
      className={`inline-flex w-fit items-center rounded-full border font-mono font-medium uppercase leading-none tracking-[0.08em] ${sizeClass} ${CLAIM_STYLES[normalized]}`}
    >
      {normalized}
    </span>
  );
}
