import { createHash } from "node:crypto";
import { lstat, readFile, realpath } from "node:fs/promises";
import path from "node:path";

import type {
  ClaimLevel,
  PortfolioArtifactRole,
  PortfolioDownloadArtifact,
  PortfolioDownloadId,
  PortfolioRouteArtifact,
  PortfolioRouteManifest,
} from "./types";

export const PORTFOLIO_CURRENT_MANIFEST = "reports/portfolio/current.json";

export const REQUIRED_PORTFOLIO_ARTIFACT_ROLES = [
  "dossier",
  "runPassport",
  "providers",
  "workflow",
  "procurement",
  "reproduction",
  "manifest",
  "dataReadiness",
  "procurementPack",
  "applicationPack",
  "pilotPlan",
] as const satisfies readonly PortfolioArtifactRole[];

const CLAIM_LEVELS = new Set<ClaimLevel>([
  "demo",
  "proxy",
  "calibrated",
  "real-data",
  "procurement-ready",
]);
const REQUIRED_ROLE_SET = new Set<string>(REQUIRED_PORTFOLIO_ARTIFACT_ROLES);
export const REQUIRED_PORTFOLIO_DOWNLOAD_IDS = [
  "dossier-html",
  "dossier-json",
  "kpis-csv",
  "run-passport-json",
  "procurement-index-json",
] as const satisfies readonly PortfolioDownloadId[];
const REQUIRED_DOWNLOAD_ID_SET = new Set<string>(REQUIRED_PORTFOLIO_DOWNLOAD_IDS);
const DOWNLOAD_MEDIA_TYPES = new Set<PortfolioDownloadArtifact["mediaType"]>([
  "text/html",
  "application/json",
  "text/csv",
]);
const SHA256_PATTERN = /^[a-f0-9]{64}$/;
const RUN_ID_PATTERN = /^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$/;
const ISO_DATE_TIME_PATTERN = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$/;
const HASHED_SOURCE_KINDS = new Set(["asset", "config", "data", "schema", "upstream-artifact"]);
const SOURCE_KINDS = new Set([...HASHED_SOURCE_KINDS, "code", "documentation"]);
const REQUIRED_RUNTIME_SOURCE_ROLES = ["roadsGeojson"] as const;

export type PortfolioSourceRecord = {
  role: string;
  path: string;
  kind: "asset" | "config" | "data" | "schema" | "upstream-artifact" | "code" | "documentation";
  required: boolean;
  sha256: string | null;
};

export type LoadedPortfolioSource = {
  record: PortfolioSourceRecord;
  content: Buffer;
  bytes: number;
  sha256: string;
};

export type LoadedPortfolioRelease = {
  manifest: PortfolioRouteManifest;
  artifacts: Record<PortfolioArtifactRole, unknown>;
  sources: Record<string, LoadedPortfolioSource>;
  runRoot: string;
};

export class PortfolioReleaseError extends Error {
  readonly code: string;

  constructor(code: string, message: string) {
    super(message);
    this.name = "PortfolioReleaseError";
    this.code = code;
  }
}

function fail(code: string, message: string): never {
  throw new PortfolioReleaseError(code, message);
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function assertExactKeys(value: Record<string, unknown>, expected: readonly string[], label: string) {
  const actual = Object.keys(value).sort();
  const required = [...expected].sort();
  if (actual.length !== required.length || actual.some((key, index) => key !== required[index])) {
    fail("manifest_contract_invalid", `${label} has unexpected or missing fields.`);
  }
}

function parseString(value: unknown, label: string): string {
  if (typeof value !== "string" || value.length === 0) {
    fail("manifest_contract_invalid", `${label} must be a non-empty string.`);
  }
  return value;
}

function parseClaimLevel(value: unknown, label: string): ClaimLevel {
  const level = parseString(value, label) as ClaimLevel;
  if (!CLAIM_LEVELS.has(level)) {
    fail("manifest_contract_invalid", `${label} has an unknown claim level.`);
  }
  return level;
}

function parseSha256(value: unknown, label: string): string {
  const digest = parseString(value, label);
  if (!SHA256_PATTERN.test(digest)) {
    fail("manifest_contract_invalid", `${label} must be a lowercase SHA-256 digest.`);
  }
  return digest;
}

function parseSafeRelativePath(value: unknown, label: string): string {
  const relativePath = parseString(value, label);
  if (
    relativePath.includes("\\") ||
    relativePath.includes(".staging") ||
    path.posix.isAbsolute(relativePath) ||
    /^[A-Za-z]:/.test(relativePath) ||
    relativePath.split("/").some((part) => part === "" || part === "." || part === "..") ||
    path.posix.normalize(relativePath) !== relativePath
  ) {
    fail("manifest_path_invalid", `${label} is not a normalized logical path.`);
  }
  return relativePath;
}

function parseArtifact(value: unknown): PortfolioRouteArtifact {
  if (!isRecord(value)) fail("manifest_contract_invalid", "Artifact entry must be an object.");
  assertExactKeys(
    value,
    ["role", "runId", "logicalPath", "sha256", "bytes", "mediaType", "claimLevel"],
    "Artifact entry",
  );

  const role = parseString(value.role, "artifact.role");
  if (!REQUIRED_ROLE_SET.has(role)) {
    fail("manifest_contract_invalid", `Unknown artifact role: ${role}.`);
  }
  const bytes = value.bytes;
  if (!Number.isSafeInteger(bytes) || (bytes as number) < 0) {
    fail("manifest_contract_invalid", "artifact.bytes must be a non-negative safe integer.");
  }
  const mediaType = parseString(value.mediaType, "artifact.mediaType");
  if (mediaType !== "application/json") {
    fail("manifest_contract_invalid", `Artifact ${role} must use application/json.`);
  }

  return {
    role: role as PortfolioArtifactRole,
    runId: parseString(value.runId, "artifact.runId"),
    logicalPath: parseSafeRelativePath(value.logicalPath, "artifact.logicalPath"),
    sha256: parseSha256(value.sha256, "artifact.sha256"),
    bytes: bytes as number,
    mediaType,
    claimLevel: parseClaimLevel(value.claimLevel, "artifact.claimLevel"),
  };
}

function parseDownloadArtifact(value: unknown): PortfolioDownloadArtifact {
  if (!isRecord(value)) fail("manifest_contract_invalid", "Download entry must be an object.");
  assertExactKeys(
    value,
    ["id", "runId", "logicalPath", "sha256", "bytes", "mediaType", "filename"],
    "Download entry",
  );
  const id = parseString(value.id, "download.id");
  if (!REQUIRED_DOWNLOAD_ID_SET.has(id)) {
    fail("manifest_contract_invalid", `Unknown download id: ${id}.`);
  }
  const bytes = value.bytes;
  if (!Number.isSafeInteger(bytes) || (bytes as number) <= 0) {
    fail("manifest_contract_invalid", "download.bytes must be a positive safe integer.");
  }
  const mediaType = parseString(value.mediaType, "download.mediaType") as PortfolioDownloadArtifact["mediaType"];
  if (!DOWNLOAD_MEDIA_TYPES.has(mediaType)) {
    fail("manifest_contract_invalid", `Download ${id} has an unsupported media type.`);
  }
  const filename = parseString(value.filename, "download.filename");
  if (!/^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$/.test(filename)) {
    fail("manifest_contract_invalid", "download.filename must be ASCII-safe.");
  }
  return {
    id: id as PortfolioDownloadId,
    runId: parseString(value.runId, "download.runId"),
    logicalPath: parseSafeRelativePath(value.logicalPath, "download.logicalPath"),
    sha256: parseSha256(value.sha256, "download.sha256"),
    bytes: bytes as number,
    mediaType,
    filename,
  };
}

export function parseRouteManifest(value: unknown): PortfolioRouteManifest {
  if (!isRecord(value)) fail("manifest_contract_invalid", "Route manifest must be an object.");
  assertExactKeys(
    value,
    [
      "schemaVersion",
      "runId",
      "scenarioId",
      "claimLevel",
      "generatedAt",
      "status",
      "sourceManifest",
      "artifacts",
      "downloads",
      "aliases",
    ],
    "Route manifest",
  );

  if (value.schemaVersion !== "portfolio-route-manifest/v1") {
    fail("manifest_contract_invalid", "Unsupported route manifest schemaVersion.");
  }
  const runId = parseString(value.runId, "manifest.runId");
  if (!RUN_ID_PATTERN.test(runId) || runId === "." || runId === "..") {
    fail("manifest_contract_invalid", "manifest.runId is unsafe.");
  }
  if (value.scenarioId !== "abay-signal-retiming") {
    fail("manifest_contract_invalid", "The promoted release belongs to another scenario.");
  }
  if (value.status !== "promoted") {
    fail("manifest_not_promoted", "The current route manifest is not promoted.");
  }
  const generatedAt = parseString(value.generatedAt, "manifest.generatedAt");
  if (!ISO_DATE_TIME_PATTERN.test(generatedAt) || Number.isNaN(Date.parse(generatedAt))) {
    fail("manifest_contract_invalid", "manifest.generatedAt must be an ISO date-time.");
  }

  if (!isRecord(value.sourceManifest)) {
    fail("manifest_contract_invalid", "manifest.sourceManifest must be an object.");
  }
  assertExactKeys(value.sourceManifest, ["path", "sha256"], "manifest.sourceManifest");
  if (value.sourceManifest.path !== "portfolio.sources.json") {
    fail("manifest_contract_invalid", "manifest.sourceManifest.path must be portfolio.sources.json.");
  }

  if (!Array.isArray(value.artifacts)) {
    fail("manifest_contract_invalid", "manifest.artifacts must be an array.");
  }
  const artifacts = value.artifacts.map(parseArtifact);
  if (artifacts.length !== REQUIRED_PORTFOLIO_ARTIFACT_ROLES.length) {
    fail("manifest_contract_invalid", "The promoted release must contain the complete route artifact set.");
  }
  const roles = new Set(artifacts.map((artifact) => artifact.role));
  if (roles.size !== artifacts.length || REQUIRED_PORTFOLIO_ARTIFACT_ROLES.some((role) => !roles.has(role))) {
    fail("manifest_contract_invalid", "Artifact roles must be complete and unique.");
  }
  if (new Set(artifacts.map((artifact) => artifact.logicalPath)).size !== artifacts.length) {
    fail("manifest_contract_invalid", "Artifact logical paths must be unique.");
  }
  if (artifacts.some((artifact) => artifact.runId !== runId)) {
    fail("mixed_release", "Artifact entries do not all belong to the promoted run.");
  }

  if (!Array.isArray(value.downloads)) {
    fail("manifest_contract_invalid", "manifest.downloads must be an array.");
  }
  const downloads = value.downloads.map(parseDownloadArtifact);
  if (downloads.length !== REQUIRED_PORTFOLIO_DOWNLOAD_IDS.length) {
    fail("manifest_contract_invalid", "The promoted release must contain the complete download allowlist.");
  }
  const downloadIds = new Set(downloads.map((download) => download.id));
  if (
    downloadIds.size !== downloads.length ||
    REQUIRED_PORTFOLIO_DOWNLOAD_IDS.some((id) => !downloadIds.has(id))
  ) {
    fail("manifest_contract_invalid", "Download IDs must be complete and unique.");
  }
  if (new Set(downloads.map((download) => download.logicalPath)).size !== downloads.length) {
    fail("manifest_contract_invalid", "Download logical paths must be unique.");
  }
  if (downloads.some((download) => download.runId !== runId)) {
    fail("mixed_release", "Download entries do not all belong to the promoted run.");
  }

  if (!isRecord(value.aliases)) {
    fail("manifest_contract_invalid", "manifest.aliases must be an object.");
  }
  assertExactKeys(value.aliases, ["status", "errors", "paths"], "manifest.aliases");
  if (!["pending", "synced", "failed"].includes(String(value.aliases.status))) {
    fail("manifest_contract_invalid", "manifest.aliases.status is invalid.");
  }
  if (
    !Array.isArray(value.aliases.errors) ||
    value.aliases.errors.some((item) => typeof item !== "string" || item.length === 0)
  ) {
    fail("manifest_contract_invalid", "manifest.aliases.errors must be a string array.");
  }
  if (!Array.isArray(value.aliases.paths)) {
    fail("manifest_contract_invalid", "manifest.aliases.paths must be an array.");
  }
  const aliasPaths = value.aliases.paths.map((item, index) => {
    if (!isRecord(item)) fail("manifest_contract_invalid", `aliases.paths[${index}] must be an object.`);
    assertExactKeys(item, ["role", "path"], `aliases.paths[${index}]`);
    const role = parseString(item.role, `aliases.paths[${index}].role`);
    if (!REQUIRED_ROLE_SET.has(role)) {
      fail("manifest_contract_invalid", `Unknown alias role: ${role}.`);
    }
    return {
      role: role as PortfolioArtifactRole,
      path: parseSafeRelativePath(item.path, `aliases.paths[${index}].path`),
    };
  });
  if (aliasPaths.length !== REQUIRED_PORTFOLIO_ARTIFACT_ROLES.length) {
    fail("manifest_contract_invalid", "Alias paths must contain the complete route artifact set.");
  }
  const aliasRoles = new Set(aliasPaths.map((item) => item.role));
  if (
    aliasRoles.size !== aliasPaths.length ||
    REQUIRED_PORTFOLIO_ARTIFACT_ROLES.some((role) => !aliasRoles.has(role))
  ) {
    fail("manifest_contract_invalid", "Alias roles must be complete and unique.");
  }
  if (new Set(aliasPaths.map((item) => item.path)).size !== aliasPaths.length) {
    fail("manifest_contract_invalid", "Alias paths must be unique.");
  }

  return {
    schemaVersion: "portfolio-route-manifest/v1",
    runId,
    scenarioId: "abay-signal-retiming",
    claimLevel: parseClaimLevel(value.claimLevel, "manifest.claimLevel"),
    generatedAt,
    status: "promoted",
    sourceManifest: {
      path: parseSafeRelativePath(value.sourceManifest.path, "manifest.sourceManifest.path"),
      sha256: parseSha256(value.sourceManifest.sha256, "manifest.sourceManifest.sha256"),
    },
    artifacts,
    downloads,
    aliases: {
      status: value.aliases.status as "pending" | "synced" | "failed",
      errors: [...(value.aliases.errors as string[])],
      paths: aliasPaths,
    },
  };
}

export function parseSourceManifest(value: unknown): PortfolioSourceRecord[] {
  if (!isRecord(value)) fail("manifest_contract_invalid", "Source manifest must be an object.");
  assertExactKeys(value, ["schemaVersion", "scenarioId", "sources"], "Source manifest");
  if (value.schemaVersion !== "portfolio-sources/v1") {
    fail("manifest_contract_invalid", "Unsupported source manifest schemaVersion.");
  }
  if (value.scenarioId !== "abay-signal-retiming") {
    fail("manifest_contract_invalid", "The source manifest belongs to another scenario.");
  }
  if (!Array.isArray(value.sources) || value.sources.length === 0) {
    fail("manifest_contract_invalid", "Source manifest must declare at least one source.");
  }

  const roles = new Set<string>();
  const paths = new Set<string>();
  const records = value.sources.map((item, index) => {
    if (!isRecord(item)) fail("manifest_contract_invalid", `sources[${index}] must be an object.`);
    const allowed = new Set(["role", "path", "kind", "required", "sha256"]);
    const actual = Object.keys(item);
    if (
      actual.some((key) => !allowed.has(key)) ||
      !["role", "path", "kind", "required"].every((key) => key in item)
    ) {
      fail("manifest_contract_invalid", `sources[${index}] has unexpected or missing fields.`);
    }

    const role = parseString(item.role, `sources[${index}].role`);
    const sourcePath = parseSafeRelativePath(item.path, `sources[${index}].path`);
    const kind = parseString(item.kind, `sources[${index}].kind`);
    if (!SOURCE_KINDS.has(kind)) {
      fail("manifest_contract_invalid", `sources[${index}].kind is unsupported.`);
    }
    if (typeof item.required !== "boolean") {
      fail("manifest_contract_invalid", `sources[${index}].required must be boolean.`);
    }
    const sourceSha =
      item.sha256 === undefined || item.sha256 === null
        ? null
        : parseSha256(item.sha256, `sources[${index}].sha256`);
    if (HASHED_SOURCE_KINDS.has(kind) && sourceSha === null) {
      fail("manifest_contract_invalid", `Hashed source ${role} requires sha256.`);
    }
    if (roles.has(role) || paths.has(sourcePath)) {
      fail("manifest_contract_invalid", "Source roles and paths must be unique.");
    }
    roles.add(role);
    paths.add(sourcePath);
    return {
      role,
      path: sourcePath,
      kind: kind as PortfolioSourceRecord["kind"],
      required: item.required,
      sha256: sourceSha,
    };
  });
  if (REQUIRED_RUNTIME_SOURCE_ROLES.some((role) => !roles.has(role))) {
    fail("manifest_contract_invalid", "Source manifest is missing a required runtime source role.");
  }
  return records;
}

function sha256(content: Buffer) {
  return createHash("sha256").update(content).digest("hex");
}

function isInside(parent: string, candidate: string) {
  const relative = path.relative(parent, candidate);
  return relative !== "" && !relative.startsWith(`..${path.sep}`) && relative !== ".." && !path.isAbsolute(relative);
}

async function readVerifiedFile(
  root: string,
  logicalPath: string,
  expectedBytes: number | null,
  expectedSha256: string | null,
) {
  const candidate = path.resolve(root, ...logicalPath.split("/"));
  if (!isInside(root, candidate)) fail("manifest_path_invalid", "An artifact path escapes its release root.");

  const metadata = await lstat(candidate).catch(() => null);
  if (!metadata?.isFile() || metadata.isSymbolicLink()) {
    fail("artifact_missing", "A promoted artifact is missing or not a regular file.");
  }
  const canonicalCandidate = await realpath(candidate);
  const canonicalRoot = await realpath(root);
  if (!isInside(canonicalRoot, canonicalCandidate)) {
    fail("manifest_path_invalid", "A promoted artifact resolves outside its release root.");
  }

  const content = await readFile(canonicalCandidate);
  if (expectedBytes !== null && content.byteLength !== expectedBytes) {
    fail("artifact_stale", "A promoted artifact has an unexpected byte length.");
  }
  if (expectedSha256 !== null && sha256(content) !== expectedSha256) {
    fail("artifact_stale", "A promoted artifact hash does not match the current manifest.");
  }
  return content;
}

function parseJsonArtifact(content: Buffer, role: string): unknown {
  try {
    return JSON.parse(content.toString("utf8"));
  } catch {
    fail("artifact_invalid", `The promoted ${role} artifact is not valid JSON.`);
  }
}

const RELEASE_BINDING_PATHS: Partial<Record<PortfolioArtifactRole, readonly string[]>> = {
  dossier: ["trustMetadata", "runId"],
  runPassport: ["runId"],
  reproduction: ["releaseRunId"],
  manifest: ["runId"],
};

function validateReleaseRunBinding(
  payload: unknown,
  role: PortfolioArtifactRole,
  expectedRunId: string,
) {
  const bindingPath = RELEASE_BINDING_PATHS[role];
  if (!bindingPath) return;

  let value: unknown = payload;
  for (const key of bindingPath) {
    if (!isRecord(value) || !(key in value)) {
      fail("mixed_release", `The promoted ${role} artifact is missing its release binding.`);
    }
    value = value[key];
  }
  if (value !== expectedRunId) {
    fail("mixed_release", `The promoted ${role} artifact belongs to another release run.`);
  }
}

export async function loadPromotedPortfolioRelease(
  cwd = process.cwd(),
  requestedRunId?: string,
): Promise<LoadedPortfolioRelease> {
  const workspaceRoot = await realpath(cwd);
  if (
    requestedRunId !== undefined &&
    (!RUN_ID_PATTERN.test(requestedRunId) || requestedRunId === "." || requestedRunId === "..")
  ) {
    fail("manifest_contract_invalid", "Requested portfolio runId is unsafe.");
  }

  const runsRoot = path.resolve(workspaceRoot, "reports", "portfolio", "runs");
  if (!isInside(workspaceRoot, runsRoot)) fail("manifest_path_invalid", "Portfolio runs path is unsafe.");
  const runsRootMetadata = await lstat(runsRoot).catch(() => null);
  if (!runsRootMetadata?.isDirectory() || runsRootMetadata.isSymbolicLink()) {
    fail("manifest_path_invalid", "Portfolio runs root must be a regular directory.");
  }
  const canonicalRunsRoot = await realpath(runsRoot);
  if (!isInside(workspaceRoot, canonicalRunsRoot)) {
    fail("manifest_path_invalid", "Portfolio runs root resolves outside the workspace.");
  }

  const manifestPath = requestedRunId
    ? path.resolve(runsRoot, requestedRunId, "route-manifest.json")
    : path.resolve(workspaceRoot, PORTFOLIO_CURRENT_MANIFEST);
  const manifestBoundary = requestedRunId ? canonicalRunsRoot : workspaceRoot;
  if (!isInside(manifestBoundary, manifestPath)) fail("manifest_path_invalid", "Route manifest path is unsafe.");

  const manifestMetadata = await lstat(manifestPath).catch(() => null);
  if (!manifestMetadata?.isFile() || manifestMetadata.isSymbolicLink()) {
    fail("manifest_missing", "No promoted portfolio route manifest is available.");
  }
  const canonicalManifestPath = await realpath(manifestPath);
  if (!isInside(manifestBoundary, canonicalManifestPath)) {
    fail("manifest_path_invalid", "Route manifest resolves outside its trusted boundary.");
  }
  const manifest = parseRouteManifest(parseJsonArtifact(await readFile(canonicalManifestPath), "route manifest"));
  if (requestedRunId !== undefined && manifest.runId !== requestedRunId) {
    fail("mixed_release", "The requested immutable manifest belongs to another run.");
  }

  const runRoot = path.resolve(runsRoot, manifest.runId);
  if (!isInside(runsRoot, runRoot)) fail("manifest_path_invalid", "Promoted run root is unsafe.");
  const runMetadata = await lstat(runRoot).catch(() => null);
  if (!runMetadata?.isDirectory() || runMetadata.isSymbolicLink()) {
    fail("artifact_missing", "The promoted run directory is missing or unsafe.");
  }
  const canonicalRunRoot = await realpath(runRoot);
  if (!isInside(canonicalRunsRoot, canonicalRunRoot)) {
    fail("manifest_path_invalid", "The promoted run resolves outside the portfolio runs root.");
  }

  const sourceContent = await readVerifiedFile(
    canonicalRunRoot,
    manifest.sourceManifest.path,
    null,
    manifest.sourceManifest.sha256,
  );
  const sourceRecords = parseSourceManifest(parseJsonArtifact(sourceContent, "source manifest"));
  const sourceEntries = await Promise.all(
    sourceRecords.map(async (record): Promise<[string, LoadedPortfolioSource] | null> => {
      const candidate = path.resolve(canonicalRunRoot, ...record.path.split("/"));
      const metadata = await lstat(candidate).catch(() => null);
      if (metadata === null && !record.required) return null;
      const content = await readVerifiedFile(canonicalRunRoot, record.path, null, record.sha256);
      return [
        record.role,
        {
          record,
          content,
          bytes: content.byteLength,
          sha256: sha256(content),
        },
      ];
    }),
  );
  const sources = Object.fromEntries(
    sourceEntries.filter((entry): entry is [string, LoadedPortfolioSource] => entry !== null),
  );

  const loaded = {} as Record<PortfolioArtifactRole, unknown>;
  await Promise.all(
    manifest.artifacts.map(async (artifact) => {
      const content = await readVerifiedFile(
        canonicalRunRoot,
        artifact.logicalPath,
        artifact.bytes,
        artifact.sha256,
      );
      const payload = parseJsonArtifact(content, artifact.role);
      validateReleaseRunBinding(payload, artifact.role, manifest.runId);
      loaded[artifact.role] = payload;
    }),
  );

  return { manifest, artifacts: loaded, sources, runRoot: canonicalRunRoot };
}

export async function loadVerifiedPortfolioDownload(
  release: LoadedPortfolioRelease,
  requestedId: string,
): Promise<{ artifact: PortfolioDownloadArtifact; content: Buffer }> {
  const artifact = release.manifest.downloads.find((download) => download.id === requestedId);
  if (!artifact) {
    fail("download_not_found", "The requested evidence download is not available.");
  }
  if (artifact.runId !== release.manifest.runId) {
    fail("mixed_release", "The requested evidence download belongs to another release run.");
  }
  return {
    artifact,
    content: await readVerifiedFile(release.runRoot, artifact.logicalPath, artifact.bytes, artifact.sha256),
  };
}

export function validateRoadProviderEvidence(
  registry: unknown,
  source: LoadedPortfolioSource | undefined,
  featureCount: number,
): Record<string, unknown> {
  if (
    !source ||
    source.record.role !== "roadsGeojson" ||
    source.record.kind !== "data" ||
    source.record.required !== true ||
    source.record.sha256 === null
  ) {
    fail("artifact_stale", "The immutable release does not declare a pinned required roads source.");
  }
  if (!isRecord(registry) || !Array.isArray(registry.providers)) {
    fail("artifact_invalid", "The provider registry is invalid.");
  }
  const provider = registry.providers.find(
    (item): item is Record<string, unknown> => isRecord(item) && item.id === "roads-geojson",
  );
  if (
    !provider ||
    provider.available !== true ||
    provider.claim_label !== "real-data" ||
    provider.path !== source.record.path ||
    provider.sha256 !== source.sha256 ||
    provider.bytes !== source.bytes ||
    provider.feature_count !== featureCount
  ) {
    fail("artifact_stale", "The roads provider evidence does not match the immutable source record.");
  }
  return provider;
}

export function isPortfolioReleaseError(error: unknown): error is PortfolioReleaseError {
  return error instanceof PortfolioReleaseError;
}
