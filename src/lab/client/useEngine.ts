"use client";

import { useSyncExternalStore } from "react";
import type { PeriodId, Scenario } from "../engine/types";
import { DATA_URL } from "./data";
import type { RunResult, WorkerResponse } from "./protocol";

export interface EngineProgress {
  stage: "baseline" | "routing";
  iteration: number;
  gap: number;
}

export interface EngineState {
  ready: boolean;
  /** Periods whose baseline routes are computed and ready for instant runs. */
  warmPeriods: PeriodId[];
  progress: EngineProgress | null;
  error: string | null;
}

const INITIAL: EngineState = { ready: false, warmPeriods: [], progress: null, error: null };

/**
 * One engine worker per browser tab, shared by every page. Client-side
 * navigation keeps it alive, so the home page can compute today's baseline
 * routes while the visitor reads, and the lab starts warm.
 */
class EngineClient {
  private static instance: EngineClient | null = null;
  private worker: Worker;
  private state: EngineState = INITIAL;
  private listeners = new Set<() => void>();
  private pending = new Map<number, { resolve: (r: RunResult) => void; reject: (e: Error) => void }>();
  private nextId = 1;

  static get(): EngineClient {
    if (!EngineClient.instance) EngineClient.instance = new EngineClient();
    return EngineClient.instance;
  }

  private constructor() {
    this.worker = new Worker(new URL("./engine.worker.ts", import.meta.url), { type: "module" });
    this.worker.onmessage = (event: MessageEvent<WorkerResponse>) => this.receive(event.data);
    this.worker.onerror = () =>
      this.set({ error: "The traffic engine stopped unexpectedly. Reload the page to try again." });
    this.worker.postMessage({ type: "init", baseUrl: new URL(DATA_URL, window.location.origin).toString() });
    this.worker.postMessage({ type: "baseline", period: "am" });
  }

  private set(patch: Partial<EngineState>) {
    this.state = { ...this.state, ...patch };
    for (const l of this.listeners) l();
  }

  private receive(message: WorkerResponse) {
    switch (message.type) {
      case "ready":
        this.set({ ready: true });
        break;
      case "baselineReady":
        this.set({ warmPeriods: [...new Set([...this.state.warmPeriods, message.period])] });
        break;
      case "progress":
        if (message.id > 0) this.set({ progress: message });
        break;
      case "result": {
        const p = this.pending.get(message.result.id);
        this.pending.delete(message.result.id);
        this.set({ progress: null });
        p?.resolve(message.result);
        break;
      }
      case "error": {
        if (message.id !== undefined) {
          const p = this.pending.get(message.id);
          this.pending.delete(message.id);
          p?.reject(new Error(message.message));
        }
        this.set({ progress: null, error: message.message });
        break;
      }
    }
  }

  subscribe = (listener: () => void) => {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  };

  getState = () => this.state;

  warm = (period: PeriodId) => {
    this.worker.postMessage({ type: "baseline", period });
  };

  run = (scenario: Scenario) => {
    const id = this.nextId++;
    this.set({ error: null, progress: { stage: "routing", iteration: 0, gap: 1 } });
    return new Promise<RunResult>((resolve, reject) => {
      this.pending.set(id, { resolve, reject });
      this.worker.postMessage({ type: "run", id, scenario });
    });
  };
}

/** Starts the engine early (e.g. on the home page) without subscribing to it. */
export function prewarmEngine() {
  EngineClient.get();
}

const noop = () => () => {};
const serverState = () => INITIAL;

export function useEngine() {
  const client = typeof window === "undefined" ? null : EngineClient.get();
  const state = useSyncExternalStore(client?.subscribe ?? noop, client?.getState ?? serverState, serverState);
  return {
    ...state,
    run: client ? client.run : () => Promise.reject(new Error("The engine runs in the browser only.")),
    warm: client ? client.warm : () => {},
  };
}
