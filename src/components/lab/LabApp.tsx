"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import { baselineFlow, baselineVc, streetBbox } from "@/lab/client/baseline";
import { useCityData, type CityData } from "@/lab/client/data";
import type { RunResult } from "@/lab/client/protocol";
import { useEngine } from "@/lab/client/useEngine";
import { decodeScenario, encodeScenario, emptyScenario } from "@/lab/engine/scenario";
import type { Change, PeriodId, Scenario } from "@/lab/engine/types";
import { EXAMPLES, resolveExample } from "@/lab/examples";
import LabMap, { type MapColoring } from "./LabMap";
import { DevelopmentCard, Intro, ScenarioBar, SearchBox, SectionCard } from "./Panel";
import ResultView from "./ResultView";
import styles from "./Lab.module.css";
import { LOAD_GRADIENT } from "./colors";

type Selection = { kind: "section"; id: number } | { kind: "point"; lon: number; lat: number } | null;
export type ResultLayer = "change" | "before" | "after";

function initialScenario(data: CityData, params: URLSearchParams): Scenario {
  const encoded = params.get("s");
  if (encoded) {
    const decoded = decodeScenario(encoded, data.graph.sections.length);
    if (decoded) return decoded;
  }
  const example = EXAMPLES.find((e) => e.id === params.get("example"));
  if (example) return resolveExample(data.graph, example);
  return emptyScenario("am");
}

export default function LabApp() {
  const { data, error } = useCityData();
  if (error) {
    return (
      <div className={styles.fullMessage} role="alert">
        <p className="title">The city model could not be loaded.</p>
        <p className="body">{error}. Check your connection and reload the page.</p>
      </div>
    );
  }
  if (!data) {
    return (
      <div className={styles.fullMessage} role="status" aria-live="polite">
        <p className="label">Loading</p>
        <p className="title">Loading 3,500 junctions and 6,900 road links…</p>
      </div>
    );
  }
  return <Lab data={data} />;
}

function Lab({ data }: { data: CityData }) {
  const params = useSearchParams();
  const engine = useEngine();
  const [scenario, setScenario] = useState<Scenario>(() => initialScenario(data, params));
  const [selection, setSelection] = useState<Selection>(null);
  const [placing, setPlacing] = useState(false);
  const [result, setResult] = useState<RunResult | null>(null);
  const [layer, setLayer] = useState<ResultLayer>("change");
  const [focus, setFocus] = useState<[number, number, number, number] | null>(null);
  const [runError, setRunError] = useState<string | null>(null);

  const scenarioKey = encodeScenario(scenario);
  const showingResult = result !== null && encodeScenario(result.scenario) === scenarioKey;

  // Keep the scenario in the address bar so any state can be shared.
  useEffect(() => {
    const url = new URL(window.location.href);
    url.searchParams.delete("example");
    if (scenario.changes.length > 0 || scenario.period !== "am") url.searchParams.set("s", scenarioKey);
    else url.searchParams.delete("s");
    window.history.replaceState(null, "", url);
  }, [scenario, scenarioKey]);

  const { warm } = engine;
  useEffect(() => {
    warm(scenario.period);
  }, [scenario.period, warm]);

  const run = useCallback(async () => {
    if (scenario.changes.length === 0) return;
    setRunError(null);
    setSelection(null);
    setPlacing(false);
    try {
      const r = await engine.run(scenario);
      setResult(r);
      setLayer("change");
      setFocus(resultBbox(data, r));
    } catch (e) {
      setRunError(e instanceof Error ? e.message : "The model could not finish this scenario.");
    }
  }, [engine, scenario, data]);

  // Examples and shared links open straight on their result.
  const pendingAutoRun = useRef(params.has("example") || params.has("s"));
  useEffect(() => {
    if (!pendingAutoRun.current || !engine.ready || scenario.changes.length === 0) return;
    pendingAutoRun.current = false;
    void run();
  }, [engine.ready, scenario.changes.length, run]);

  const update = (next: Scenario) => {
    setScenario(next);
    setRunError(null);
  };
  const addChange = (change: Change) => {
    // Re-applying the same change to the same section replaces it instead of stacking.
    const others = scenario.changes.filter((c) => {
      if (change.type === "development" || c.type === "development") return true;
      return !(c.section === change.section && c.type === change.type);
    });
    update({ ...scenario, changes: [...others, change].slice(-12) });
    setSelection(null);
    setPlacing(false);
  };
  const removeChange = (index: number) => update({ ...scenario, changes: scenario.changes.filter((_, i) => i !== index) });
  const setPeriod = (period: PeriodId) => update({ ...scenario, period });
  const reset = () => {
    update(emptyScenario(scenario.period));
    setResult(null);
    setSelection(null);
    setPlacing(false);
  };

  const coloring: MapColoring = useMemo(() => {
    if (showingResult && result) {
      if (layer === "change") return { kind: "diff", before: result.baseFlow, after: result.flow };
      if (layer === "after") return { kind: "load", flow: result.flow, vc: result.vc };
    }
    return { kind: "load", flow: baselineFlow(data, scenario.period), vc: baselineVc(data, scenario.period) };
  }, [showingResult, result, layer, data, scenario.period]);

  const selectSection = (id: number) => {
    setPlacing(false);
    setSelection({ kind: "section", id });
  };

  return (
    <div className={styles.lab}>
      <div className={styles.mapArea}>
        <LabMap
          data={data}
          coloring={coloring}
          selectedSection={selection?.kind === "section" ? selection.id : null}
          changes={scenario.changes}
          placing={placing}
          focus={focus}
          pendingPoint={placing && selection?.kind === "point" ? selection : null}
          onPickSection={selectSection}
          onPickPoint={(lon, lat) => setSelection({ kind: "point", lon, lat })}
          onClear={() => !placing && setSelection(null)}
        />
        <Legend coloring={coloring} />
        {placing && <div className={styles.mapHint}>Click anywhere on the map to place the building</div>}
      </div>

      <aside className={styles.panel} aria-label="Scenario">
        {showingResult && result ? (
          <ResultView
            data={data}
            result={result}
            layer={layer}
            onLayer={setLayer}
            onEdit={() => setResult(null)}
            onReset={reset}
            onFocusStreet={(street) => setFocus(streetBbox(data, street))}
          />
        ) : (
          <>
            <div className={styles.panelBody}>
              <div className={styles.block}>
                <p className="label">Time of day</p>
                <div className="segmented" role="group" aria-label="Time of day">
                  {(["am", "midday", "pm", "night"] as PeriodId[]).map((p) => (
                    <button key={p} type="button" aria-pressed={scenario.period === p} onClick={() => setPeriod(p)}>
                      {{ am: "Morning", midday: "Midday", pm: "Evening", night: "Night" }[p]}
                    </button>
                  ))}
                </div>
              </div>
              <SearchBox
                data={data}
                onPick={(section) => {
                  selectSection(section);
                  setFocus(data.graph.sections[section].bbox);
                }}
              />
              {selection?.kind === "section" ? (
                <SectionCard
                  data={data}
                  period={scenario.period}
                  section={selection.id}
                  scenario={scenario}
                  onAdd={addChange}
                  onClose={() => setSelection(null)}
                />
              ) : placing ? (
                <DevelopmentCard
                  point={selection?.kind === "point" ? selection : null}
                  onAdd={addChange}
                  onCancel={() => {
                    setPlacing(false);
                    setSelection(null);
                  }}
                />
              ) : (
                <Intro
                  data={data}
                  onPlace={() => {
                    setSelection(null);
                    setPlacing(true);
                  }}
                  onExample={(s) => {
                    pendingAutoRun.current = true;
                    update(s);
                    setResult(null);
                  }}
                  hasChanges={scenario.changes.length > 0}
                />
              )}
            </div>
            <ScenarioBar
              data={data}
              scenario={scenario}
              engine={engine}
              error={runError}
              onRemove={removeChange}
              onRun={run}
              onReset={reset}
            />
          </>
        )}
      </aside>
    </div>
  );
}

/** The changed sections and new buildings, with ~1.5 km of surroundings. */
function resultBbox(data: CityData, r: RunResult): [number, number, number, number] | null {
  const boxes = r.scenario.changes.map((c) =>
    c.type === "development" ? [c.lon, c.lat, c.lon, c.lat] : data.graph.sections[c.section].bbox,
  );
  if (boxes.length === 0) return null;
  const padLon = 0.02;
  const padLat = 0.014;
  return [
    Math.min(...boxes.map((b) => b[0])) - padLon,
    Math.min(...boxes.map((b) => b[1])) - padLat,
    Math.max(...boxes.map((b) => b[2])) + padLon,
    Math.max(...boxes.map((b) => b[3])) + padLat,
  ];
}

function Legend({ coloring }: { coloring: MapColoring }) {
  return (
    <div className={styles.legend} aria-hidden="true">
      {coloring.kind === "load" ? (
        <>
          <span className="label">Traffic load</span>
          <span className={styles.legendBar} style={{ background: LOAD_GRADIENT }} />
          <span className={styles.legendScale}>
            <span>Free-flowing</span>
            <span>Jammed</span>
          </span>
        </>
      ) : (
        <>
          <span className="label">Change in traffic</span>
          <span className={styles.legendDiff}>
            <span>
              <i style={{ background: "var(--less)" }} /> Less
            </span>
            <span>
              <i style={{ background: "#cfccc3" }} /> Same
            </span>
            <span>
              <i style={{ background: "var(--more)" }} /> More
            </span>
          </span>
        </>
      )}
    </div>
  );
}
