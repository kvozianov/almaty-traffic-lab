"use client";

import { useId, useMemo, useState } from "react";
import { sectionStats } from "@/lab/client/baseline";
import type { CityData } from "@/lab/client/data";
import type { useEngine } from "@/lab/client/useEngine";
import { isChangeAvailable } from "@/lab/engine/scenario";
import type { Change, DevelopmentKind, PeriodId, Scenario, SectionChangeType } from "@/lab/engine/types";
import { EXAMPLES, resolveExample } from "@/lab/examples";
import { CHANGE_LABELS, DEVELOPMENT_LABELS, describeChange, formatInt, PERIOD_LABELS } from "@/lab/format";
import { Icon, type IconName } from "./Icon";
import styles from "./Lab.module.css";

/* ------------------------------------------------------------ search */

export function SearchBox({ data, onPick }: { data: CityData; onPick: (section: number) => void }) {
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const listId = useId();
  const matches = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (q.length < 2) return [];
    // Street-name matches first (prefix before substring), then cross-street matches.
    const scored: [number, number][] = [];
    data.graph.sections.forEach((s, i) => {
      const name = data.graph.streets[s.street].name.toLowerCase();
      const score = name.startsWith(q) ? 0 : name.includes(q) ? 1 : data.searchIndex[i].includes(q) ? 2 : -1;
      if (score >= 0) scored.push([score, i]);
    });
    scored.sort((a, b) => a[0] - b[0] || a[1] - b[1]);
    return scored.slice(0, 8).map(([, i]) => i);
  }, [query, data]);

  return (
    <div className={styles.search}>
      <label className="label" htmlFor={`${listId}-input`}>
        Find a street
      </label>
      <input
        id={`${listId}-input`}
        className="input"
        type="search"
        placeholder="Abay, Tole Bi, Al-Farabi…"
        value={query}
        autoComplete="off"
        role="combobox"
        aria-expanded={open && matches.length > 0}
        aria-controls={listId}
        onChange={(e) => {
          setQuery(e.target.value);
          setOpen(true);
        }}
        onFocus={() => setOpen(true)}
        onBlur={() => setTimeout(() => setOpen(false), 150)}
      />
      {open && matches.length > 0 && (
        <ul className={styles.searchList} id={listId} role="listbox">
          {matches.map((i) => {
            const s = data.graph.sections[i];
            return (
              <li key={i} role="option" aria-selected={false}>
                <button
                  type="button"
                  onMouseDown={(e) => e.preventDefault()}
                  onClick={() => {
                    onPick(i);
                    setQuery("");
                    setOpen(false);
                  }}
                >
                  <span>{data.graph.streets[s.street].name}</span>
                  <span className={styles.muted}>{s.label}</span>
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}

/* ------------------------------------------------------------ intro */

const STEPS = [
  ["01", "Pick a street", "Click any coloured road on the map, or search for it."],
  ["02", "Change it", "Close it, give a lane to buses, retime its signals…"],
  ["03", "See what happens", "275,000 morning trips find new routes in your browser."],
];

export function Intro({
  data,
  onPlace,
  onExample,
  hasChanges,
}: {
  data: CityData;
  onPlace: () => void;
  onExample: (s: Scenario) => void;
  hasChanges: boolean;
}) {
  return (
    <>
      {!hasChanges && (
        <ol className={styles.steps}>
          {STEPS.map(([n, title, text]) => (
            <li key={n}>
              <span className="label">{n}</span>
              <div>
                <p className={styles.stepTitle}>{title}</p>
                <p className="small">{text}</p>
              </div>
            </li>
          ))}
        </ol>
      )}
      <button type="button" className={`btn btn-secondary ${styles.placeButton}`} onClick={onPlace}>
        <Icon name="building" /> Place a new building
      </button>
      <div className={styles.block}>
        <p className="label">Or start from a question</p>
        <ul className={styles.examples}>
          {EXAMPLES.map((ex) => (
            <li key={ex.id}>
              <button type="button" onClick={() => onExample(resolveExample(data.graph, ex))}>
                <span>{ex.title}</span>
                <span className={styles.muted}>{PERIOD_LABELS[ex.period].long}</span>
              </button>
            </li>
          ))}
        </ul>
      </div>
    </>
  );
}

/* ------------------------------------------------------------ section card */

const SECTION_ACTIONS: { type: SectionChangeType; icon: IconName }[] = [
  { type: "close", icon: "barrier" },
  { type: "busLane", icon: "bus" },
  { type: "addLane", icon: "plus" },
  { type: "greenWave", icon: "signal" },
  { type: "speedLimit", icon: "gauge" },
];

const UNAVAILABLE: Partial<Record<SectionChangeType, string>> = {
  busLane: "Only one lane each way: a bus lane would close it to cars.",
  greenWave: "No traffic signals on this stretch.",
};

export function SectionCard({
  data,
  period,
  section,
  scenario,
  onAdd,
  onClose,
}: {
  data: CityData;
  period: PeriodId;
  section: number;
  scenario: Scenario;
  onAdd: (c: Change) => void;
  onClose: () => void;
}) {
  const s = data.graph.sections[section];
  const stats = sectionStats(data, period, section);
  const applied = new Set(
    scenario.changes.flatMap((c) => (c.type !== "development" && c.section === section ? [c.type] : [])),
  );
  const load = Math.round(stats.maxVc * 100);

  return (
    <section className={styles.card} aria-label="Selected street">
      <div className={styles.cardHead}>
        <div>
          <p className="label">Selected · {PERIOD_LABELS[period].long}</p>
          <h2 className="title">{data.graph.streets[s.street].name}</h2>
          <p className="small">{s.label}</p>
        </div>
        <button type="button" className="btn btn-quiet" onClick={onClose} aria-label="Close">
          <Icon name="close" />
        </button>
      </div>
      <dl className={styles.stats}>
        <div>
          <dt className="label">Cars / hour</dt>
          <dd className="num">{formatInt(stats.maxFlow)}</dd>
        </div>
        <div>
          <dt className="label">Load</dt>
          <dd className="num">{load}%</dd>
        </div>
        <div>
          <dt className="label">Lanes</dt>
          <dd className="num">{stats.lanes} each way</dd>
        </div>
        <div>
          <dt className="label">Signals</dt>
          <dd className="num">{stats.signals}</dd>
        </div>
      </dl>
      <p className="label" style={{ marginTop: 20 }}>
        What should change?
      </p>
      <ul className={styles.actions}>
        {SECTION_ACTIONS.map(({ type, icon }) => {
          const available = isChangeAvailable(data.graph, type, section);
          const label = CHANGE_LABELS[type];
          return (
            <li key={type}>
              <button
                type="button"
                disabled={!available}
                aria-pressed={applied.has(type)}
                onClick={() => onAdd(type === "speedLimit" ? { type, section, kmh: 40 } : { type, section })}
              >
                <Icon name={icon} />
                <span>
                  <span className={styles.actionTitle}>{label.title}</span>
                  <span className={styles.muted}>{available ? label.detail : UNAVAILABLE[type]}</span>
                </span>
                {applied.has(type) && <span className="label">Added</span>}
              </button>
            </li>
          );
        })}
      </ul>
    </section>
  );
}

/* ------------------------------------------------------------ development */

export function DevelopmentCard({
  point,
  onAdd,
  onCancel,
}: {
  point: { lon: number; lat: number } | null;
  onAdd: (c: Change) => void;
  onCancel: () => void;
}) {
  const [kind, setKind] = useState<DevelopmentKind>("housing");
  const [sizeIndex, setSizeIndex] = useState(1);
  const meta = DEVELOPMENT_LABELS[kind];
  return (
    <section className={styles.card} aria-label="New building">
      <div className={styles.cardHead}>
        <div>
          <p className="label">New building</p>
          <h2 className="title">{point ? "Choose type and size" : "Click the map to place it"}</h2>
          <p className="small">
            {point
              ? `${point.lat.toFixed(4)}° N, ${point.lon.toFixed(4)}° E`
              : "New trips start and end at the point you choose."}
          </p>
        </div>
        <button type="button" className="btn btn-quiet" onClick={onCancel} aria-label="Cancel">
          <Icon name="close" />
        </button>
      </div>
      <p className="label" style={{ marginTop: 20 }}>
        Type
      </p>
      <div className="segmented" role="group" aria-label="Building type">
        {(Object.keys(DEVELOPMENT_LABELS) as DevelopmentKind[]).map((k) => (
          <button key={k} type="button" aria-pressed={kind === k} onClick={() => setKind(k)}>
            {DEVELOPMENT_LABELS[k].title.split(" ")[0]}
          </button>
        ))}
      </div>
      <p className="label" style={{ marginTop: 16 }}>
        Size
      </p>
      <div className="segmented" role="group" aria-label="Size">
        {meta.sizes.map((size, i) => (
          <button key={size} type="button" aria-pressed={sizeIndex === i} onClick={() => setSizeIndex(i)}>
            {formatInt(size)}
          </button>
        ))}
      </div>
      <p className="small" style={{ marginTop: 8 }}>
        {meta.unit}
      </p>
      <button
        type="button"
        className="btn btn-primary btn-block"
        style={{ marginTop: 16 }}
        disabled={!point}
        onClick={() => point && onAdd({ type: "development", kind, size: meta.sizes[sizeIndex], lon: point.lon, lat: point.lat })}
      >
        Add to scenario
      </button>
    </section>
  );
}

/* ------------------------------------------------------------ scenario bar */

export function ScenarioBar({
  data,
  scenario,
  engine,
  error,
  onRemove,
  onRun,
  onReset,
}: {
  data: CityData;
  scenario: Scenario;
  engine: ReturnType<typeof useEngine>;
  error: string | null;
  onRemove: (i: number) => void;
  onRun: () => void;
  onReset: () => void;
}) {
  const running = engine.progress !== null;
  const count = scenario.changes.length;
  return (
    <div className={styles.scenarioBar}>
      <div className={styles.scenarioHead}>
        <p className="label">Your scenario{count > 0 ? ` · ${count}` : ""}</p>
        {count > 0 && !running && (
          <button type="button" className="btn btn-quiet" onClick={onReset}>
            Clear
          </button>
        )}
      </div>
      {count === 0 ? (
        <p className="small">No changes yet. Pick a street to start.</p>
      ) : (
        <ol className={styles.changeList}>
          {scenario.changes.map((c, i) => {
            const d = describeChange(data.graph, c);
            return (
              <li key={i}>
                <span className="label">{String(i + 1).padStart(2, "0")}</span>
                <span className={styles.changeText}>
                  <span>{d.title}</span>
                  <span className={styles.muted}>{d.detail}</span>
                </span>
                <button
                  type="button"
                  className="btn btn-quiet"
                  aria-label={`Remove ${d.title}`}
                  disabled={running}
                  onClick={() => onRemove(i)}
                >
                  <Icon name="close" />
                </button>
              </li>
            );
          })}
        </ol>
      )}
      {error && (
        <p className={styles.error} role="alert">
          {error}
        </p>
      )}
      {running ? (
        <Progress engine={engine} />
      ) : (
        <button type="button" className="btn btn-primary btn-block" disabled={count === 0} onClick={onRun}>
          See what happens
        </button>
      )}
    </div>
  );
}

function Progress({ engine }: { engine: ReturnType<typeof useEngine> }) {
  const p = engine.progress!;
  const text =
    p.stage === "baseline"
      ? "Working out today’s traffic first…"
      : p.iteration === 0
        ? "Starting the model…"
        : "Drivers are finding new routes…";
  // The gap shrinks geometrically; show it on a log scale from 100 % to the 0.05 % target.
  const done = p.iteration === 0 ? 0.04 : Math.min(1, Math.max(0.05, Math.log10(1 / Math.max(p.gap, 5e-4)) / Math.log10(2000)));
  return (
    <div className={styles.progress} role="status" aria-live="polite">
      <div className={styles.progressTrack}>
        <div className={styles.progressBar} style={{ transform: `scaleX(${done})` }} />
      </div>
      <p className="small">{text}</p>
      <p className="label">
        Iteration {p.iteration} · equilibrium gap {p.iteration === 0 ? "—" : `${(p.gap * 100).toFixed(2)}%`}
      </p>
    </div>
  );
}
