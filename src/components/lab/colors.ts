export type RGBA = [number, number, number, number];

function hex(h: string, a = 255): RGBA {
  const n = Number.parseInt(h.slice(1), 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255, a];
}

function mix(a: RGBA, b: RGBA, t: number): RGBA {
  return [
    Math.round(a[0] + (b[0] - a[0]) * t),
    Math.round(a[1] + (b[1] - a[1]) * t),
    Math.round(a[2] + (b[2] - a[2]) * t),
    Math.round(a[3] + (b[3] - a[3]) * t),
  ];
}

/**
 * Load (demand / capacity) ramp: quiet sage → ochre → red → deep red. Static
 * assignment lets demand exceed capacity (delay grows instead), so the ramp
 * keeps going past 1.0.
 */
const LOAD_STOPS: [number, RGBA][] = [
  [0, hex("#a9bdaf", 210)],
  [0.6, hex("#9db08f")],
  [0.85, hex("#d8b65a")],
  [1.1, hex("#dc8a3c")],
  [1.4, hex("#c4442b")],
  [1.9, hex("#7e1f1a")],
];

const UNUSED = hex("#d9d6cd", 200);

export function loadColor(vc: number): RGBA {
  if (vc < 0.02) return UNUSED;
  for (let i = 1; i < LOAD_STOPS.length; i++) {
    const [x1, c1] = LOAD_STOPS[i];
    if (vc <= x1) {
      const [x0, c0] = LOAD_STOPS[i - 1];
      return mix(c0, c1, (vc - x0) / (x1 - x0));
    }
  }
  return LOAD_STOPS[LOAD_STOPS.length - 1][1];
}

export const LOAD_GRADIENT = `linear-gradient(90deg, ${LOAD_STOPS.map(
  ([x, c]) => `rgb(${c[0]} ${c[1]} ${c[2]}) ${Math.round((x / 1.9) * 100)}%`,
).join(", ")})`;

const MORE = hex("#c4442b");
const LESS = hex("#2f6e8e");
const SAME = hex("#cfccc3", 150);

/** Below these thresholds a change is treated as model noise and shown as unchanged. */
export const DIFF_MIN_VEHICLES = 50;
export const DIFF_MIN_SHARE = 0.05;

export function diffColor(before: number, after: number): RGBA {
  const d = after - before;
  const share = Math.abs(d) / Math.max(before, 100);
  if (Math.abs(d) < DIFF_MIN_VEHICLES || share < DIFF_MIN_SHARE) return SAME;
  const t = Math.min(1, 0.35 + share * 1.3);
  const target = d > 0 ? MORE : LESS;
  return mix(hex("#e8e5dd"), target, t);
}

