/** Outline icons on a 20px grid, one 1.5px stroke weight. */
const PATHS = {
  building: "M4 17V5.5L10 3l6 2.5V17M2.5 17h15M7.5 7.5h1M11.5 7.5h1M7.5 10.5h1M11.5 10.5h1M8.5 17v-3h3v3",
  barrier: "M3 8h14v4H3zM6 12v5M14 12v5M6 8l3-0M8 8l4 4M12 8l4 4M4 12l0 0",
  bus: "M5 15V5a2 2 0 0 1 2-2h6a2 2 0 0 1 2 2v10M4.5 15h11M5 9.5h10M7 15v2M13 15v2M7.5 12.5h.01M12.5 12.5h.01",
  plus: "M10 4v12M4 10h12",
  signal: "M7 2.5h6v15H7zM10 5.5h.01M10 10h.01M10 14.5h.01",
  gauge: "M3.5 13.5a6.5 6.5 0 1 1 13 0M10 13.5l3-4M3.5 13.5h2M14.5 13.5h2",
  close: "M5 5l10 10M15 5L5 15",
  link: "M8.5 11.5l3-3M7 9l-1.5 1.5a2.5 2.5 0 0 0 3.5 3.5L10.5 12.5M13 11l1.5-1.5a2.5 2.5 0 0 0-3.5-3.5L9.5 7.5",
  report: "M5.5 2.5h6l3 3v12h-9zM11.5 2.5v3h3M7.5 9.5h5M7.5 12.5h5M7.5 15h3",
  back: "M12 4.5L6.5 10l5.5 5.5",
  up: "M10 15V5M5.5 9.5L10 5l4.5 4.5",
  down: "M10 5v10M5.5 10.5L10 15l4.5-4.5",
  download: "M10 3v10M5.5 8.5L10 13l4.5-4.5M4 16.5h12",
  print: "M5.5 7.5v-5h9v5M5.5 14H3.5V8h13v6h-2M5.5 11.5h9v6h-9z",
} as const;

export type IconName = keyof typeof PATHS;

export function Icon({ name, size = 18 }: { name: IconName; size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 20 20"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      style={{ flex: "none" }}
    >
      <path d={PATHS[name]} />
    </svg>
  );
}
