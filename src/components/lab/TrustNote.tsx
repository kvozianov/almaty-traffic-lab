import Link from "next/link";
import styles from "./Lab.module.css";

export const TRUST_ITEMS: { level: "real" | "standard" | "estimate"; title: string; text: string }[] = [
  {
    level: "real",
    title: "Road network and traffic signals",
    text: "Almaty’s main road network (6,900 one-way links) and 665 signals from OpenStreetMap, April 2026.",
  },
  {
    level: "standard",
    title: "Road capacity",
    text: "Engineering rule of thumb per lane and road type, not measured on Almaty streets.",
  },
  {
    level: "estimate",
    title: "Who drives where",
    text: "Estimated from where homes and jobs are likely to be. Almaty has no public trip survey.",
  },
  {
    level: "estimate",
    title: "Checked against real travel times",
    text: "Not yet. The overall scale is set so the morning peak averages about 27 km/h.",
  },
];

const MARK = { real: "●", standard: "◐", estimate: "○" };

export default function TrustNote({ compact = false }: { compact?: boolean }) {
  return (
    <details className={styles.trust} open={!compact}>
      <summary>
        <span className="label">How much to trust this</span>
        <span className={styles.trustDots} aria-label="2 out of 5">
          ●●○○○
        </span>
      </summary>
      <p className="small" style={{ marginTop: 8 }}>
        Trust the direction and the relative size of changes more than the exact numbers.
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
        How the model works →
      </Link>
    </details>
  );
}
