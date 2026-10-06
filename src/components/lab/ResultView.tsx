"use client";

import { useState } from "react";
import Link from "next/link";
import type { CityData } from "@/lab/client/data";
import type { RunResult } from "@/lab/client/protocol";
import { encodeScenario } from "@/lab/engine/scenario";
import { formatInt, formatNumber, formatSigned, percentChange } from "@/lab/format";
import { headline, METRIC_ROWS, notableStreets, periodLabel } from "@/lab/summary";
import { Icon } from "./Icon";
import type { ResultLayer } from "./LabApp";
import TrustNote from "./TrustNote";
import styles from "./Lab.module.css";

export default function ResultView({
  data,
  result,
  layer,
  onLayer,
  onEdit,
  onReset,
  onFocusStreet,
}: {
  data: CityData;
  result: RunResult;
  layer: ResultLayer;
  onLayer: (l: ResultLayer) => void;
  onEdit: () => void;
  onReset: () => void;
  onFocusStreet: (street: number) => void;
}) {
  const [copied, setCopied] = useState(false);
  const { baseline, metrics } = result;
  const streets = notableStreets(result.streets, 6);
  const encoded = encodeScenario(result.scenario);
  const trips = metrics.trips - baseline.trips;

  const copy = async () => {
    const url = `${window.location.origin}/lab?s=${encoded}`;
    try {
      await navigator.clipboard.writeText(url);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      window.prompt("Copy this link", url);
    }
  };

  return (
    <div className={styles.panelBody}>
      <button type="button" className={`btn btn-quiet ${styles.backButton}`} onClick={onEdit}>
        <Icon name="back" /> Edit scenario
      </button>

      <div className={styles.block}>
        <p className="label">Result · {periodLabel(result.scenario.period)}</p>
        <h2 className={styles.headline}>{headline(data.graph, result)}</h2>
      </div>

      <dl className={styles.metrics}>
        {METRIC_ROWS.map((row) => {
          const before = baseline[row.key];
          const after = metrics[row.key];
          const pct = percentChange(before, after);
          const tone = Math.abs(pct) < 0.05 ? "" : pct > 0 ? styles.worse : styles.better;
          return (
            <div key={row.key}>
              <dt className="small">{row.label}</dt>
              <dd>
                <span className={`${styles.metricValue} ${tone}`}>{formatSigned(pct, 1, "%")}</span>
                <span className="label">
                  {formatNumber(before, row.digits)} → {formatNumber(after, row.digits)} {row.unit}
                </span>
              </dd>
            </div>
          );
        })}
      </dl>
      {trips > 0.5 && (
        <p className="small">
          The new building adds about {formatInt(trips)} car trips in this hour.
        </p>
      )}
      {metrics.unservedTrips > 0.5 && (
        <p className={styles.error} role="status">
          {formatInt(metrics.unservedTrips)} trips have no route left. The change cuts some places off the main road
          network.
        </p>
      )}

      <div className={styles.block}>
        <p className="label">Show on map</p>
        <div className="segmented" role="group" aria-label="Map layer">
          {(
            [
              ["change", "Change"],
              ["before", "Before"],
              ["after", "After"],
            ] as [ResultLayer, string][]
          ).map(([key, label]) => (
            <button key={key} type="button" aria-pressed={layer === key} onClick={() => onLayer(key)}>
              {label}
            </button>
          ))}
        </div>
      </div>

      <div className={styles.block}>
        <p className="label">Where traffic moved</p>
        {streets.length === 0 ? (
          <p className="small">No street changed by more than a few percent.</p>
        ) : (
          <ul className={styles.streetList}>
            {streets.map((s) => (
              <li key={s.street}>
                <button type="button" onClick={() => onFocusStreet(s.street)}>
                  <span>
                    {s.name}
                    {s.changed && <span className={styles.inlineMuted}> · your change</span>}
                  </span>
                  <span className={`num ${s.trafficPct > 0 ? styles.worse : styles.better}`}>
                    <Icon name={s.trafficPct > 0 ? "up" : "down"} size={14} />
                    {formatSigned(s.trafficPct, 0, "%")}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>

      <TrustNote compact />

      <div className={styles.resultActions}>
        <Link className="btn btn-primary" href={`/lab/report?s=${encoded}`}>
          <Icon name="report" /> Full report
        </Link>
        <button type="button" className="btn btn-secondary" onClick={copy}>
          <Icon name="link" /> {copied ? "Link copied" : "Copy link"}
        </button>
        <button type="button" className="btn btn-quiet" onClick={onReset}>
          Start over
        </button>
      </div>
      <p className="label">
        Solved in {result.convergence.iterations} iterations · {(result.convergence.ms / 1000).toFixed(1)} s · run{" "}
        {result.passport.resultHash.slice(0, 10)}
      </p>
    </div>
  );
}
