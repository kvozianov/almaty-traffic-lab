import { access } from "node:fs/promises";
import path from "node:path";
import { spawn } from "node:child_process";

import { NextRequest, NextResponse } from "next/server";

import {
  isPortfolioReleaseError,
  loadPromotedPortfolioRelease,
} from "@/components/dossier/portfolioRelease";
import {
  buildChildEnvironment,
  bootstrapSummaryMatchesRelease,
  parseCanonicalBootstrapSummary,
  type BootstrapSummary,
} from "@/components/dossier/generationBoundary";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const EXPECTED_SCENARIO_ID = "abay-signal-retiming";
const MAX_BODY_BYTES = 1024;
const MAX_CHILD_OUTPUT_BYTES = 64 * 1024;
const CHILD_TIMEOUT_MS = 120_000;

class RequestFailure extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
    message: string,
  ) {
    super(message);
    this.name = "RequestFailure";
  }
}

type BootstrapResult = {
  stdout: string;
  stderr: string;
  exitCode: number | null;
  signal: NodeJS.Signals | null;
  timedOut: boolean;
  outputOverflow: boolean;
};

function generationEnabled() {
  return (
    process.env.TRAFFIC_SIM_ENABLE_PORTFOLIO_GENERATION === "1" &&
    process.env.NODE_ENV !== "production"
  );
}

async function readBoundedJson(request: NextRequest): Promise<Record<string, unknown>> {
  const contentType = request.headers.get("content-type")?.split(";", 1)[0]?.trim().toLowerCase();
  if (contentType !== "application/json") {
    throw new RequestFailure(415, "content_type_invalid", "Content-Type must be application/json.");
  }

  const declaredLength = request.headers.get("content-length");
  if (declaredLength) {
    const bytes = Number(declaredLength);
    if (!Number.isSafeInteger(bytes) || bytes < 0 || bytes > MAX_BODY_BYTES) {
      throw new RequestFailure(413, "body_too_large", "Request body exceeds 1 KiB.");
    }
  }

  const reader = request.body?.getReader();
  if (!reader) throw new RequestFailure(400, "body_required", "A JSON request body is required.");
  const chunks: Uint8Array[] = [];
  let bytesRead = 0;

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    bytesRead += value.byteLength;
    if (bytesRead > MAX_BODY_BYTES) {
      await reader.cancel();
      throw new RequestFailure(413, "body_too_large", "Request body exceeds 1 KiB.");
    }
    chunks.push(value);
  }

  const merged = new Uint8Array(bytesRead);
  let offset = 0;
  for (const chunk of chunks) {
    merged.set(chunk, offset);
    offset += chunk.byteLength;
  }

  let body: unknown;
  try {
    body = JSON.parse(new TextDecoder("utf-8", { fatal: true }).decode(merged));
  } catch {
    throw new RequestFailure(400, "json_invalid", "Request body must be valid UTF-8 JSON.");
  }
  if (typeof body !== "object" || body === null || Array.isArray(body)) {
    throw new RequestFailure(400, "body_invalid", "Request body must be a JSON object.");
  }
  return body as Record<string, unknown>;
}

function validateBody(body: Record<string, unknown>) {
  const keys = Object.keys(body);
  if (keys.length !== 1 || keys[0] !== "scenarioId") {
    throw new RequestFailure(
      400,
      "body_contract_invalid",
      "Only {\"scenarioId\":\"abay-signal-retiming\"} is accepted.",
    );
  }
  if (body.scenarioId !== EXPECTED_SCENARIO_ID) {
    throw new RequestFailure(400, "scenario_not_allowed", "Unknown or unsafe scenarioId.");
  }
}

async function resolvePythonInterpreter() {
  const configured = process.env.TRAFFIC_SIM_PYTHON;
  if (configured) return configured;

  const venvPython = path.join(
    /* turbopackIgnore: true */ process.cwd(),
    ".venv",
    "bin",
    "python",
  );
  try {
    await access(venvPython);
    return venvPython;
  } catch {
    return "python3";
  }
}

function runBootstrap(interpreter: string): Promise<BootstrapResult> {
  return new Promise((resolve, reject) => {
    const child = spawn(interpreter, ["scripts/bootstrap_portfolio.py"], {
      cwd: process.cwd(),
      env: buildChildEnvironment(),
      shell: false,
      stdio: ["ignore", "pipe", "pipe"],
    });
    const stdout: Buffer[] = [];
    const stderr: Buffer[] = [];
    let outputBytes = 0;
    let timedOut = false;
    let outputOverflow = false;
    let stopping = false;
    let hardKillTimer: NodeJS.Timeout | undefined;

    const stopChild = () => {
      if (stopping) return;
      stopping = true;
      child.kill("SIGTERM");
      hardKillTimer = setTimeout(() => child.kill("SIGKILL"), 1_000);
      hardKillTimer.unref();
    };
    const append = (target: Buffer[], chunk: Buffer) => {
      if (outputOverflow) return;
      outputBytes += chunk.byteLength;
      if (outputBytes > MAX_CHILD_OUTPUT_BYTES) {
        outputOverflow = true;
        stopChild();
        return;
      }
      target.push(chunk);
    };

    child.stdout.on("data", (chunk: Buffer) => append(stdout, chunk));
    child.stderr.on("data", (chunk: Buffer) => append(stderr, chunk));
    child.once("error", reject);

    const timeout = setTimeout(() => {
      timedOut = true;
      stopChild();
    }, CHILD_TIMEOUT_MS);
    timeout.unref();

    child.once("close", (exitCode, signal) => {
      clearTimeout(timeout);
      if (hardKillTimer) clearTimeout(hardKillTimer);
      resolve({
        stdout: Buffer.concat(stdout).toString("utf8"),
        stderr: Buffer.concat(stderr).toString("utf8"),
        exitCode,
        signal,
        timedOut,
        outputOverflow,
      });
    });
  });
}

export function parseBootstrapSummary(stdout: string): BootstrapSummary {
  try {
    return parseCanonicalBootstrapSummary(stdout);
  } catch {
    throw new RequestFailure(502, "bootstrap_output_invalid", "Portfolio bootstrap returned invalid JSON.");
  }
}

export async function POST(request: NextRequest) {
  if (!generationEnabled()) {
    return NextResponse.json({ error: "Not found." }, { status: 404 });
  }

  try {
    validateBody(await readBoundedJson(request));
    const result = await runBootstrap(await resolvePythonInterpreter());

    if (result.timedOut) {
      throw new RequestFailure(504, "bootstrap_timeout", "Portfolio bootstrap exceeded 120 seconds.");
    }
    if (result.outputOverflow) {
      throw new RequestFailure(502, "bootstrap_output_too_large", "Portfolio bootstrap output exceeded 64 KiB.");
    }

    const processOutput = `${result.stdout}\n${result.stderr}`;
    if (result.exitCode !== 0) {
      if (result.exitCode === 75 || /lock[_ -]?timeout|lock[_ -]?contention/i.test(processOutput)) {
        throw new RequestFailure(409, "bootstrap_lock_timeout", "Another portfolio bootstrap is active.");
      }
      throw new RequestFailure(502, "bootstrap_failed", "Portfolio bootstrap failed before promotion.");
    }

    const summary = parseBootstrapSummary(result.stdout);
    const release = await loadPromotedPortfolioRelease();
    if (!bootstrapSummaryMatchesRelease(summary, release.manifest.runId)) {
      throw new RequestFailure(
        409,
        "bootstrap_release_superseded",
        "Another portfolio release was promoted before this response could be bound.",
      );
    }
    const status = summary.status;
    const warning =
      status === "promoted_with_alias_error"
        ? "Immutable evidence was promoted, but one or more non-authoritative aliases were not refreshed."
        : status === "promoted_with_warning"
          ? "Immutable evidence was promoted, but a post-promotion durability or notification step reported a warning."
          : undefined;

    return NextResponse.json(
      {
        manifest: release.manifest,
        generation: {
          status,
          warning,
        },
      },
      {
        status: 201,
        headers: { "Cache-Control": "no-store" },
      },
    );
  } catch (error) {
    if (error instanceof RequestFailure) {
      return NextResponse.json(
        { error: error.message, code: error.code },
        { status: error.status, headers: { "Cache-Control": "no-store" } },
      );
    }
    const code = isPortfolioReleaseError(error) ? error.code : "portfolio_generation_failed";
    console.error("Portfolio generation boundary failed:", error);
    return NextResponse.json(
      { error: "Portfolio generation failed.", code },
      { status: 503, headers: { "Cache-Control": "no-store" } },
    );
  }
}
