/** Two crossing streets and one marked junction. */
export default function BrandMark({ size = 22 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" aria-hidden="true">
      <rect width="32" height="32" rx="8" fill="var(--ink)" />
      <path d="M6 20h20M12 6v20" stroke="var(--bg)" strokeWidth="3" strokeLinecap="round" />
      <circle cx="12" cy="20" r="3.5" fill="var(--more)" />
    </svg>
  );
}
