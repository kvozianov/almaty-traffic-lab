import Link from "next/link";
import calibration from "../../../public/model/calibration.json";
import styles from "./Lab.module.css";

type Level = "real" | "fitted" | "standard" | "estimate";

const speedRows = calibration.fit.filter((f) => f.unit === "km/h").length;
const v = calibration.validation;

export const TRUST_ITEMS: { level: Level; title: string; text: string }[] = [
  {
    level: "real",
    title: "Road network and traffic signals",
    text: "Almaty’s main road network (6,900 one-way links) and 665 signals from OpenStreetMap, April 2026.",
  },
  {
    level: "fitted",
    title: "How busy each hour is",
    text:
      `Fitted to published Almaty measurements: Sergek ITS corridor speeds, a year-long Abay commute log and ` +
      `Yandex Traffic’s weekday profile. Median error ${Math.round(calibration.speedErrorMedian * 100)}% on ${speedRows} corridors.`,
  },
  {
    level: "fitted",
    title: "Checked on data it never saw",
    text: `${v.inTop25Percent} of Sergek’s ${v.matched} most congested junctions are among the model’s most delayed quarter in the evening peak.`,
  },
  {
    level: "estimate",
    title: "Who drives where",
    text: "Estimated from homes and jobs, pinned to the city master plan: 60% of jobs in the centre, 55% of residents outside it.",
  },
  {
    level: "standard",
    title: "Road capacity",
    text: "Engineering values per lane and road type, not measured on each Almaty street.",
  },
];

const MARK: Record<Level, string> = { real: "●", fitted: "◕", standard: "◐", estimate: "○" };

export default function TrustNote({ compact = false }: { compact?: boolean }) {
  return (
    <details className={styles.trust} open={!compact}>
      <summary>
        <span className="label">How much to trust this</span>
        <span className={styles.trustDots} aria-label="3 out of 5">
          ●●●○○
        </span>
      </summary>
      <p className="small" style={{ marginTop: 8 }}>
        Calibrated to real Almaty traffic, but on a handful of published measurements. Trust the direction and size of
        a change more than the exact minute.
      </p>
      <ul className={styles.trustList}>
        {TRUST_ITEMS.map((item) => (
          <li key={item.title}>
            <span aria-hidden="true">{MARK[item.level]}</span>
            <span>
              <span className={styles.actionTitle}>{item.title}</span>
              <span className={styles.muted}>{item.text}</span>
            </span>
          </li>
        ))}
      </ul>
      <Link href="/methods" className="small">
        How it was checked →
      </Link>
    </details>
  );
}
