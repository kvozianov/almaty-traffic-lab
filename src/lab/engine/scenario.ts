import { baseLinkInputs, type CityModel, type LinkInputs } from "./model";
import type { Change, PeriodId, Scenario } from "./types";

export const GREEN_PRIORITY = 0.6;
export const GREEN_CROSSING = 0.4;
/** Free-flow speed is this share of the posted limit (matches the graph builder). */
export const URBAN_SPEED_FACTOR = 0.85;

export const PERIODS: PeriodId[] = ["am", "midday", "pm", "night"];

export function emptyScenario(period: PeriodId = "am"): Scenario {
  return { v: 1, period, changes: [] };
}

/** Applies scenario changes to link inputs. Section changes stack in order. */
export function applyChanges(model: CityModel, changes: Change[]): LinkInputs {
  const inputs = baseLinkInputs(model);
  for (const change of changes) {
    if (change.type === "development") continue;
    const section = model.graph.sections[change.section];
    if (!section) continue;
    switch (change.type) {
      case "close":
        for (const e of section.edges) inputs.closed[e] = 1;
        break;
      case "busLane":
        for (const e of section.edges) if (inputs.lanes[e] > 1) inputs.lanes[e] -= 1;
        break;
      case "addLane":
        for (const e of section.edges) inputs.lanes[e] = Math.min(inputs.lanes[e] + 1, 8);
        break;
      case "speedLimit":
        for (const e of section.edges) {
          inputs.freeSpeed[e] = Math.min(inputs.freeSpeed[e], change.kmh * URBAN_SPEED_FACTOR);
        }
        break;
      case "greenWave": {
        const groups = new Set<number>();
        const own = new Set(section.edges);
        for (const e of section.edges) {
          if (model.signal[e]) {
            inputs.green[e] = GREEN_PRIORITY;
            groups.add(model.signalGroup[e]);
          }
        }
        // The extra green comes out of the crossing approaches at the same junctions.
        const street = section.street;
        for (let e = 0; e < model.edgeCount; e++) {
          if (!model.signal[e] || own.has(e) || model.street[e] === street) continue;
          if (groups.has(model.signalGroup[e])) inputs.green[e] = GREEN_CROSSING;
        }
        break;
      }
    }
  }
  return inputs;
}

/** Whether a change can be applied to a section (e.g. bus lane needs 2+ lanes). */
export function isChangeAvailable(model: CityModel, type: Change["type"], section: number): boolean {
  const s = model.graph.sections[section];
  if (!s) return false;
  if (type === "busLane") return s.minLanes > 1;
  if (type === "greenWave") return s.signals > 0;
  return true;
}

/* ------------------------------------------------------------ encoding */

/** JSON with sorted object keys: the canonical form used for hashing. */
export function canonicalJson(value: unknown): string {
  if (value === null || typeof value !== "object") return JSON.stringify(value);
  if (Array.isArray(value)) return `[${value.map(canonicalJson).join(",")}]`;
  const entries = Object.entries(value as Record<string, unknown>)
    .filter(([, v]) => v !== undefined)
    .sort(([a], [b]) => (a < b ? -1 : a > b ? 1 : 0));
  return `{${entries.map(([k, v]) => `${JSON.stringify(k)}:${canonicalJson(v)}`).join(",")}}`;
}

function toBase64Url(text: string): string {
  const bytes = new TextEncoder().encode(text);
  let binary = "";
  for (const b of bytes) binary += String.fromCharCode(b);
  return btoa(binary).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

function fromBase64Url(encoded: string): string {
  const b64 = encoded.replace(/-/g, "+").replace(/_/g, "/");
  const binary = atob(b64 + "=".repeat((4 - (b64.length % 4)) % 4));
  return new TextDecoder().decode(Uint8Array.from(binary, (c) => c.charCodeAt(0)));
}

export function encodeScenario(scenario: Scenario): string {
  return toBase64Url(canonicalJson(scenario));
}

/** Parses and validates a scenario from a URL parameter; returns null when invalid. */
export function decodeScenario(encoded: string, sectionCount: number): Scenario | null {
  try {
    const raw = JSON.parse(fromBase64Url(encoded)) as Partial<Scenario>;
    if (raw.v !== 1 || !PERIODS.includes(raw.period as PeriodId) || !Array.isArray(raw.changes)) return null;
    const changes: Change[] = [];
    for (const c of raw.changes.slice(0, 20) as Change[]) {
      if (c.type === "development") {
        if (!["housing", "office", "mall"].includes(c.kind)) return null;
        if (![c.lon, c.lat, c.size].every(Number.isFinite) || c.size <= 0 || c.size > 200_000) return null;
        changes.push({ type: "development", kind: c.kind, lon: c.lon, lat: c.lat, size: c.size });
      } else if (["close", "busLane", "addLane", "greenWave", "speedLimit"].includes(c.type)) {
        if (!Number.isInteger(c.section) || c.section < 0 || c.section >= sectionCount) return null;
        if (c.type === "speedLimit") {
          if (!Number.isFinite(c.kmh) || c.kmh < 10 || c.kmh > 120) return null;
          changes.push({ type: "speedLimit", section: c.section, kmh: c.kmh });
        } else changes.push({ type: c.type, section: c.section });
      } else return null;
    }
    return { v: 1, period: raw.period as PeriodId, changes };
  } catch {
    return null;
  }
}

export async function sha256Hex(text: string): Promise<string> {
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text));
  return [...new Uint8Array(digest)].map((b) => b.toString(16).padStart(2, "0")).join("");
}
