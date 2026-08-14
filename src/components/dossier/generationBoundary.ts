const CHILD_ENVIRONMENT_KEYS = [
  "PATH",
  "LANG",
  "LC_ALL",
  "LC_CTYPE",
  "TZ",
  "TMPDIR",
  "TMP",
  "TEMP",
  "SYSTEMROOT",
] as const;
const BOOTSTRAP_STATUSES = new Set([
  "promoted",
  "promoted_with_alias_error",
  "promoted_with_warning",
]);
const RUN_ID_PATTERN = /^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$/;

export type BootstrapSummary = {
  runId: string;
  status: "promoted" | "promoted_with_alias_error" | "promoted_with_warning";
};

export function buildChildEnvironment(
  source: Readonly<Record<string, string | undefined>> = process.env,
): NodeJS.ProcessEnv {
  const nodeEnv =
    source.NODE_ENV === "production" || source.NODE_ENV === "test"
      ? source.NODE_ENV
      : "development";
  const environment: NodeJS.ProcessEnv = {
    NODE_ENV: nodeEnv,
    PYTHONDONTWRITEBYTECODE: "1",
    PYTHONUTF8: "1",
  };
  for (const key of CHILD_ENVIRONMENT_KEYS) {
    const value = source[key];
    if (value !== undefined) environment[key] = value;
  }
  return environment;
}

export function parseCanonicalBootstrapSummary(stdout: string): BootstrapSummary {
  const value = JSON.parse(stdout.trim()) as unknown;
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    throw new Error("Bootstrap summary must be an object.");
  }
  const record = value as Record<string, unknown>;
  if (
    typeof record.runId !== "string" ||
    !RUN_ID_PATTERN.test(record.runId) ||
    record.runId === "." ||
    record.runId === ".." ||
    typeof record.status !== "string" ||
    !BOOTSTRAP_STATUSES.has(record.status)
  ) {
    throw new Error("Bootstrap summary has an invalid runId or status.");
  }
  return record as BootstrapSummary;
}

export function bootstrapSummaryMatchesRelease(
  summary: BootstrapSummary,
  releaseRunId: string,
): boolean {
  return summary.runId === releaseRunId;
}
