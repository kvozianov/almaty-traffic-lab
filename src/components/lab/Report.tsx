"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useCityData, type CityData } from "@/lab/client/data";
import type { RunResult } from "@/lab/client/protocol";
import { useEngine } from "@/lab/client/useEngine";
import { decodeScenario } from "@/lab/engine/scenario";
import type { Scenario } from "@/lab/engine/types";
import { describeChange, formatNumber, formatSigned, percentChange } from "@/lab/format";
import { headline, METRIC_ROWS, notableStreets, periodLabel } from "@/lab/summary";
import { Icon } from "./Icon";
import { TRUST_ITEMS } from "./TrustNote";
import styles from "./Report.module.css";

export default function Report() {
  const { data, error } = useCityData();
  const params = useSearchParams();
  const encoded = params.get("s") ?? "";
  // Memoised so the run effect below fires once per link, not once per render.
  const scenario = useMemo(
    () => (data ? decodeScenario(encoded, data.graph.sections.length) : null),
    [data, encoded],
  );
  if (error) return <Message title="The city model could not be loaded." text={error} />;
  if (!data) return <Message title="Loading the city model…" />;
  if (!scenario || scenario.changes.length === 0) {
    return <Message title="This link has no scenario." text="Open the lab, make a change and use “Full report”." />;
  }
  return <ReportBody data={data} scenario={scenario} encoded={encoded} />;
}

function Message({ title, text }: { title: string; text?: string }) {
  return (
    <div className={styles.message} role="status">
      <p className="title">{title}</p>
      {text && <p className="body">{text}</p>}
      <Link className="btn btn-secondary" href="/lab">
        Open the lab
      </Link>
    </div>
  );
}

function ReportBody({ data, scenario, encoded }: { data: CityData; scenario: Scenario; encoded: string }) {
  const engine = useEngine();
  const [result, setResult] = useState<RunResult | null>(null);
  const [failed, setFailed] = useState<string | null>(null);
  const { ready, run } = engine;

  useEffect(() => {
    if (!ready) return;
    let alive = true;
    run(scenario)
      .then((r) => alive && setResult(r))
      .catch((e: unknown) => alive && setFailed(e instanceof Error ? e.message : "The model could not finish."));
    return () => {
      alive = false;
    };
  }, [ready, run, scenario]);

  if (failed) return <Message title="The model could not finish this scenario." text={failed} />;
  if (!result) {
    return (
      <div className={styles.message} role="status" aria-live="polite">
        <p className="label">Computing</p>
        <p className="title">Re-routing 275,000 trips for this report…</p>
        {engine.progress && engine.progress.iteration > 0 && (
          <p className="small">Iteration {engine.progress.iteration}</p>
        )}
      </div>
    );
  }

  const { graph, manifest } = data;
  const streets = notableStreets(result.streets, 10);
  const created = new Date();

  const download = () => {
    const payload = {
      schema: "almaty-traffic-lab/scenario-report/v1",
      createdAt: created.toISOString(),
      link: `${window.location.origin}/lab?s=${encoded}`,
      scenario: result.scenario,
      changes: result.scenario.changes.map((c) => describeChange(graph, c)),
      baseline: result.baseline,
      result: result.metrics,
      streets: streets.map(({ name, trafficPct, vehKmDelta, delayBefore, delayAfter, changed }) => ({
        name,
        trafficPct,
        vehKmDelta,
        minutesPerKmBefore: delayBefore,
        minutesPerKmAfter: delayAfter,
        changed,
      })),
      convergence: result.convergence,
      passport: result.passport,
      data: { osmSnapshot: manifest.osmTimestamp, attribution: manifest.attribution },
      claimLevel: "proxy",
    };
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `almaty-traffic-lab-${result.passport.scenarioHash.slice(0, 8)}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <article className={styles.report}>
      <div className={`no-print ${styles.toolbar}`}>
        <Link className="btn btn-quiet" href={`/lab?s=${encoded}`}>
          <Icon name="back" /> Back to the lab
        </Link>
        <div className={styles.toolbarActions}>
          <button type="button" className="btn btn-secondary" onClick={download}>
            <Icon name="download" /> JSON
          </button>
          <button type="button" className="btn btn-primary" onClick={() => window.print()}>
            <Icon name="print" /> Print or save PDF
          </button>
        </div>
      </div>

      <header className={styles.header}>
        <p className="label">Scenario report · Almaty Traffic Lab</p>
        <h1 className={styles.title}>{headline(graph, result)}</h1>
        <p className="small">
          {periodLabel(result.scenario.period)} · generated{" "}
          {created.toLocaleDateString("en-GB", { day: "numeric", month: "long", year: "numeric" })} · model estimate,
          not a forecast
        </p>
      </header>

      <section className={styles.section}>
        <h2 className="label">01 · The scenario</h2>
        <ol className={styles.changes}>
          {result.scenario.changes.map((c, i) => {
            const d = describeChange(graph, c);
            return (
              <li key={i}>
                <span className="label">{String(i + 1).padStart(2, "0")}</span>
                <span>
                  {d.title}
                  <span className={styles.muted}>{d.detail}</span>
                </span>
              </li>
            );
          })}
        </ol>
      </section>

      <section className={styles.section}>
        <h2 className="label">02 · City-wide effect</h2>
        <table className={styles.table}>
          <thead>
            <tr>
              <th scope="col">Measure</th>
              <th scope="col">Today</th>
              <th scope="col">With the change</th>
              <th scope="col">Change</th>
            </tr>
          </thead>
          <tbody>
            {METRIC_ROWS.map((row) => {
              const before = result.baseline[row.key];
              const after = result.metrics[row.key];
              return (
                <tr key={row.key}>
                  <th scope="row">
                    {row.label}
                    <span className={styles.muted}>{row.hint}</span>
                  </th>
                  <td className="num">
                    {formatNumber(before, row.digits)} {row.unit}
                  </td>
                  <td className="num">
                    {formatNumber(after, row.digits)} {row.unit}
                  </td>
                  <td className="num">{formatSigned(percentChange(before, after), 1, "%")}</td>
                </tr>
              );
            })}
            <tr>
              <th scope="row">
                Car trips in the hour
                <span className={styles.muted}>Trips without a route are listed separately.</span>
              </th>
              <td className="num">{formatNumber(result.baseline.trips)}</td>
              <td className="num">{formatNumber(result.metrics.trips)}</td>
              <td className="num">
                {result.metrics.unservedTrips > 0.5 ? `${formatNumber(result.metrics.unservedTrips)} unrouted` : "—"}
              </td>
            </tr>
          </tbody>
        </table>
      </section>

      <section className={styles.section}>
        <h2 className="label">03 · Streets that changed most</h2>
        {streets.length === 0 ? (
          <p className="body">No street changed by more than a few percent.</p>
        ) : (
          <table className={styles.table}>
            <thead>
              <tr>
                <th scope="col">Street</th>
                <th scope="col">Traffic</th>
                <th scope="col">Minutes per km</th>
              </tr>
            </thead>
            <tbody>
              {streets.map((s) => (
                <tr key={s.street}>
                  <th scope="row">
                    {s.name}
                    {s.changed && <span className={styles.muted}>Changed in this scenario</span>}
                  </th>
                  <td className="num">{formatSigned(s.trafficPct, 0, "%")}</td>
                  <td className="num">
                    {s.delayBefore.toFixed(2)} → {s.delayAfter.toFixed(2)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      <section className={styles.section}>
        <h2 className="label">04 · How much to trust this</h2>
        <dl className={styles.trust}>
          {TRUST_ITEMS.map((t) => (
            <div key={t.title}>
              <dt>{t.title}</dt>
              <dd className="body">{t.text}</dd>
            </div>
          ))}
        </dl>
        <p className="small" style={{ marginTop: 12 }}>
          Use this report to compare options and decide what to measure next, not as a forecast of travel times.
        </p>
      </section>

      <section className={styles.section}>
        <h2 className="label">05 · Run passport</h2>
        <dl className={styles.passport}>
          <div>
            <dt>Engine</dt>
            <dd>v{result.passport.engineVersion} · path-based user equilibrium</dd>
          </div>
          <div>
            <dt>Solver</dt>
            <dd>
              {result.convergence.iterations} iterations · gap {(result.convergence.relativeGap * 100).toFixed(3)}%
            </dd>
          </div>
          <div>
            <dt>Road data</dt>
            <dd>OpenStreetMap snapshot {manifest.osmTimestamp?.slice(0, 10)}</dd>
          </div>
          <div>
            <dt>Data hash</dt>
            <dd>{result.passport.dataHash}</dd>
          </div>
          <div>
            <dt>Scenario hash</dt>
            <dd>{result.passport.scenarioHash}</dd>
          </div>
          <div>
            <dt>Result hash</dt>
            <dd>{result.passport.resultHash}</dd>
          </div>
        </dl>
        <p className="small" style={{ marginTop: 12 }}>
          Opening the same link again recomputes the scenario and gives the same result hash.
        </p>
      </section>
    </article>
  );
}
