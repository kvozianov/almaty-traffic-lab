import type { Observations } from "@/lab/engine/observed";
import type { PeriodId } from "@/lab/engine/types";
import styles from "./RealityCheck.module.css";

export interface FitRow {
  id: string;
  label: string;
  period: PeriodId;
  hours: string;
  observed: number;
  model: number;
  unit: string;
  source: string;
}

export interface CalibrationReport {
  totalTrips: number;
  periodFactors: Record<PeriodId, number>;
  beta: number;
  fit: FitRow[];
  speedErrorMedian: number;
  validation: {
    matched: number;
    inTop10Percent: number;
    inTop25Percent: number;
    medianPercentile: number | null;
    junctions: { streets: [string, string]; percentile: number | null; rank: number | null }[];
  };
}

const PERIOD_X: Record<PeriodId, number> = { am: 9, midday: 14.5, pm: 19, night: 23 };

/** Weekday congestion by hour: published Yandex points next to the model's periods. */
function ProfileChart({ obs, fit }: { obs: Observations; fit: FitRow[] }) {
  const W = 640;
  const H = 200;
  const pad = { l: 36, r: 12, t: 12, b: 28 };
  const modelPoints = fit
    .filter((f) => f.id.startsWith("tti-"))
    .map((f) => ({ period: f.period, points: (f.model - 1) * 10 }));
  // The axis grows to show every model point rather than clipping it.
  const top = Math.max(10, Math.ceil(Math.max(...modelPoints.map((m) => m.points)) / 2) * 2);
  const x = (h: number) => pad.l + (h / 24) * (W - pad.l - pad.r);
  const y = (p: number) => H - pad.b - (p / top) * (H - pad.t - pad.b);
  const published: { from: number; to: number; points: number }[] = [
    { from: 8.5, to: 9.5, points: 5 },
    { from: 12, to: 17, points: 4 },
    { from: 18.5, to: 19.5, points: 7 },
  ];
  return (
    <figure className={styles.figure}>
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Weekday congestion by hour: published Yandex points and the model">
        {Array.from({ length: top / 2 + 1 }, (_, k) => k * 2).map((p) => (
          <g key={p}>
            <line x1={pad.l} x2={W - pad.r} y1={y(p)} y2={y(p)} className={styles.grid} />
            <text x={pad.l - 8} y={y(p) + 4} className={styles.axis} textAnchor="end">
              {p}
            </text>
          </g>
        ))}
        {[0, 6, 9, 12, 15, 18, 21, 24].map((h) => (
          <text key={h} x={x(h)} y={H - 8} className={styles.axis} textAnchor="middle">
            {h === 24 ? "24" : `${h}:00`}
          </text>
        ))}
        {published.map((s) => (
          <line key={s.from} x1={x(s.from)} x2={x(s.to)} y1={y(s.points)} y2={y(s.points)} className={styles.observed} />
        ))}
        {modelPoints.map((m) => (
          <circle key={m.period} cx={x(PERIOD_X[m.period])} cy={y(Math.max(0, m.points))} r={5} className={styles.model} />
        ))}
      </svg>
      <figcaption className="small">
        <span className={styles.keyObserved} /> Yandex Traffic, weekday points (published) ·{" "}
        <span className={styles.keyModel} /> this model, travel-time index shown as points (1 point ≈ 10 % extra travel
        time — our reading of the scale). Above the black marks, the model is more congested city-wide than Yandex
        reports. {obs.timeProfile.points.some((p) => "assumed" in p) ? "Night is not published and is assumed near free flow." : ""}
      </figcaption>
    </figure>
  );
}

export default function RealityCheck({ obs, report }: { obs: Observations; report: CalibrationReport }) {
  const sourceById = new Map(obs.sources.map((s) => [s.id, s]));
  const speedRows = report.fit.filter((f) => f.unit === "km/h");
  const v = report.validation;
  return (
    <div className={styles.wrap}>
      <ProfileChart obs={obs} fit={report.fit} />

      <table className={styles.table}>
        <caption className="label">Measured speed vs the model</caption>
        <thead>
          <tr>
            <th scope="col">Where and when</th>
            <th scope="col">Measured</th>
            <th scope="col">Model</th>
            <th scope="col">Source</th>
          </tr>
        </thead>
        <tbody>
          {speedRows.map((r) => {
            const s = sourceById.get(r.source);
            return (
              <tr key={r.id}>
                <th scope="row">
                  {r.label}
                  <span className={styles.muted}>{r.hours}</span>
                </th>
                <td className="num">{r.observed} km/h</td>
                <td className="num">{r.model.toFixed(0)} km/h</td>
                <td>
                  {s ? (
                    <a href={s.url} target="_blank" rel="noreferrer">
                      {s.publisher.split(" via ")[0].split(" / ")[0]}
                    </a>
                  ) : (
                    r.source
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>

      <p className="body">
        Median speed error on these corridors: <strong>{Math.round(report.speedErrorMedian * 100)}%</strong>. A static
        model averages over the hour and cannot reproduce queues that spill back across junctions, so very slow
        stretches such as central Abay are harder to match than fast ones.
      </p>

      <div className={styles.holdout}>
        <p className="label">Hold-out check · not used for fitting</p>
        <p className="body">
          Sergek ITS published Almaty’s 15 most congested junctions (February 2025). In the model’s evening peak,{" "}
          <strong>
            {v.inTop25Percent} of {v.matched}
          </strong>{" "}
          are among the most delayed quarter of the city’s {""}signalised junctions and {v.inTop10Percent} in the top
          tenth
          {v.medianPercentile !== null ? `; the median one ranks above ${Math.round(v.medianPercentile * 100)}% of all junctions` : ""}.
        </p>
      </div>

      <dl className={styles.fitted}>
        <div>
          <dt className="label">Fitted</dt>
          <dd className="body">
            {report.totalTrips.toLocaleString("en-US")} car trips in the morning peak hour; midday{" "}
            {Math.round(report.periodFactors.midday * 100)}% and evening {Math.round(report.periodFactors.pm * 100)}% of
            that; trip-length decay {report.beta} per minute.
          </dd>
        </div>
        <div>
          <dt className="label">From the city’s master plan</dt>
          <dd className="body">
            {Math.round(obs.structure.jobsInCentreShare * 100)}% of jobs in the centre (
            {obs.structure.centre.description}), {Math.round(obs.structure.residentsOutsideCentreShare * 100)}% of residents
            outside it.
          </dd>
        </div>
      </dl>

      <ul className={styles.sources}>
        {obs.sources.map((s) => (
          <li key={s.id}>
            <a href={s.url} target="_blank" rel="noreferrer">
              {s.title}
            </a>
            <span className={styles.muted}>
              {s.publisher} · {s.date}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
