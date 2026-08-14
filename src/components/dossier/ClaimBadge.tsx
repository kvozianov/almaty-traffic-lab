import type { ClaimInput, ClaimLevel } from "./types";

const CLAIM_LEVELS: ClaimLevel[] = [
  "demo",
  "proxy",
  "calibrated",
  "real-data",
  "procurement-ready",
];

const CLAIM_STYLES: Record<ClaimLevel, string> = {
  demo: "border-stone-500/45 bg-stone-400/10 text-stone-200",
  proxy: "border-amber-500/50 bg-amber-500/10 text-amber-100",
  calibrated: "border-cyan-500/50 bg-cyan-500/10 text-cyan-100",
  "real-data": "border-emerald-500/50 bg-emerald-500/10 text-emerald-100",
  "procurement-ready": "border-teal-400/55 bg-teal-400/10 text-teal-100",
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
      className={`inline-flex w-fit items-center rounded-full border font-mono uppercase tracking-[0.08em] ${sizeClass} ${CLAIM_STYLES[normalized]}`}
    >
      {normalized}
    </span>
  );
}
