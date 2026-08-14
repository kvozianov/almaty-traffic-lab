import { strict as assert } from "node:assert";
import { createHash } from "node:crypto";
import { mkdirSync, mkdtempSync, readFileSync, rmSync, symlinkSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";

import {
  PortfolioReleaseError,
  REQUIRED_PORTFOLIO_ARTIFACT_ROLES,
  loadPromotedPortfolioRelease,
  parseRouteManifest,
  validateRoadProviderEvidence,
} from "../src/components/dossier/portfolioRelease";
import { isEmpiricalCalibrationComplete } from "../src/components/dossier/evidence";
import {
  buildChildEnvironment,
  bootstrapSummaryMatchesRelease,
  parseCanonicalBootstrapSummary,
} from "../src/components/dossier/generationBoundary";

function readFixture(name: string): unknown {
  return JSON.parse(readFileSync(path.join(process.cwd(), "tests", "fixtures", name), "utf8"));
}

const procurementRouteSource = readFileSync(
  path.join(process.cwd(), "src", "app", "api", "exports", "procurement-pack", "route.ts"),
  "utf8",
);
assert.match(procurementRouteSource, /loadPromotedPortfolioRelease\(\)/);
assert.match(procurementRouteSource, /regeneratePortfolio\(request\)/);
assert.doesNotMatch(procurementRouteSource, /generate_akimat_application_pack\.py/);
assert.doesNotMatch(procurementRouteSource, /procurement_pack_index\.json/);

function expectReleaseError(value: unknown, code: string) {
  let error: unknown;

  try {
    parseRouteManifest(value);
  } catch (caught) {
    error = caught;
  }

  assert.ok(error instanceof PortfolioReleaseError, `expected PortfolioReleaseError(${code})`);
  assert.equal(error.code, code);
}

const validFixture = readFixture("portfolio-route-manifest.valid.json");
const parsed = parseRouteManifest(validFixture);

assert.equal(parsed.runId, "portfolio-test-001");
assert.equal(parsed.scenarioId, "abay-signal-retiming");
assert.deepEqual(
  new Set(parsed.artifacts.map((artifact) => artifact.role)),
  new Set(REQUIRED_PORTFOLIO_ARTIFACT_ROLES),
);

expectReleaseError(readFixture("portfolio-route-manifest.invalid.json"), "manifest_contract_invalid");

const mixedRelease = JSON.parse(JSON.stringify(validFixture)) as {
  artifacts: Array<{ runId: string }>;
};
mixedRelease.artifacts[0].runId = "portfolio-test-002";
expectReleaseError(mixedRelease, "mixed_release");

const traversal = JSON.parse(JSON.stringify(validFixture)) as {
  artifacts: Array<{ logicalPath: string }>;
};
traversal.artifacts[0].logicalPath = "../outside.json";
expectReleaseError(traversal, "manifest_path_invalid");

const duplicateAlias = JSON.parse(JSON.stringify(validFixture)) as {
  aliases: { paths: Array<{ role: string; path: string }> };
};
duplicateAlias.aliases.paths[1] = { ...duplicateAlias.aliases.paths[0] };
expectReleaseError(duplicateAlias, "manifest_contract_invalid");

assert.equal(
  isEmpiricalCalibrationComplete({
    available: true,
    claimLabel: "proxy",
    observedVsSimulated: [],
  }),
  false,
  "a proxy assumptions file must not complete empirical validation",
);

const childEnvironment = buildChildEnvironment({
  PATH: "/usr/bin:/bin",
  LANG: "C.UTF-8",
  OPENAI_API_KEY: "must-not-cross-boundary",
  DATABASE_URL: "must-not-cross-boundary",
});
assert.equal(childEnvironment.PATH, "/usr/bin:/bin");
assert.equal(childEnvironment.LANG, "C.UTF-8");
assert.equal(childEnvironment.PYTHONDONTWRITEBYTECODE, "1");
assert.equal(childEnvironment.PYTHONUTF8, "1");
assert.equal(childEnvironment.OPENAI_API_KEY, undefined);
assert.equal(childEnvironment.DATABASE_URL, undefined);
assert.deepEqual(parseCanonicalBootstrapSummary('{"runId":"portfolio-test-001","status":"promoted"}'), {
  runId: "portfolio-test-001",
  status: "promoted",
});
assert.deepEqual(
  parseCanonicalBootstrapSummary(
    '{"runId":"portfolio-test-001","status":"promoted_with_warning"}',
  ),
  { runId: "portfolio-test-001", status: "promoted_with_warning" },
);
assert.throws(() => parseCanonicalBootstrapSummary('{"runId":"portfolio-test-001","status":"unknown"}'));
assert.throws(() => parseCanonicalBootstrapSummary('{"runId":"../escape","status":"promoted"}'));
assert.equal(
  bootstrapSummaryMatchesRelease(
    { runId: "portfolio-test-001", status: "promoted" },
    "portfolio-test-001",
  ),
  true,
);
assert.equal(
  bootstrapSummaryMatchesRelease(
    { runId: "portfolio-test-001", status: "promoted" },
    "portfolio-test-002",
  ),
  false,
  "a superseded current pointer must not be returned as the generated release",
);
assert.equal(
  isEmpiricalCalibrationComplete({
    available: true,
    claimLabel: "proxy",
    observedVsSimulated: [{ segment: "Abay" }],
  }),
  false,
  "observations cannot upgrade a proxy claim by themselves",
);
assert.equal(
  isEmpiricalCalibrationComplete({
    available: true,
    claimLabel: "calibrated",
    observedVsSimulated: [],
  }),
  false,
  "a calibrated label without comparison rows is incomplete",
);
assert.equal(
  isEmpiricalCalibrationComplete({
    available: true,
    claimLabel: "calibrated",
    observedVsSimulated: [{ segment: "Abay" }],
  }),
  true,
  "calibrated evidence with comparison rows completes the gate",
);

function digest(content: Buffer): string {
  return createHash("sha256").update(content).digest("hex");
}

async function expectAsyncReleaseError(
  operation: () => Promise<unknown>,
  code: string,
) {
  let error: unknown;
  try {
    await operation();
  } catch (caught) {
    error = caught;
  }
  assert.ok(error instanceof PortfolioReleaseError, `expected PortfolioReleaseError(${code})`);
  assert.equal(error.code, code);
}

async function verifyImmutableFilesystemBindings() {
  const workspace = mkdtempSync(path.join(tmpdir(), "almaty-route-contract-"));
  const runId = "portfolio-filesystem-001";
  const runRoot = path.join(workspace, "reports", "portfolio", "runs", runId);
  const currentPath = path.join(workspace, "reports", "portfolio", "current.json");
  const roadsContent = Buffer.from(JSON.stringify({ type: "FeatureCollection", features: [] }));
  const sourceContent = Buffer.from(
    JSON.stringify({
      schemaVersion: "portfolio-sources/v1",
      scenarioId: "abay-signal-retiming",
      sources: [
        {
          role: "roadsGeojson",
          path: "data/roads.geojson",
          kind: "data",
          required: true,
          sha256: digest(roadsContent),
        },
      ],
    }),
  );
  const artifactPayloads: Record<string, Record<string, unknown>> = {
    dossier: { trustMetadata: { runId } },
    runPassport: { runId },
    reproduction: { releaseRunId: runId },
    manifest: { runId },
    procurementPack: {
      role: "procurementPack",
      scenarioId: "abay-signal-retiming",
      marker: "immutable-promoted-pack",
    },
  };

  try {
    mkdirSync(runRoot, { recursive: true });
    const artifacts = REQUIRED_PORTFOLIO_ARTIFACT_ROLES.map((role) => {
      const logicalPath = `artifacts/${role}.json`;
      const content = Buffer.from(JSON.stringify(artifactPayloads[role] ?? { role }));
      const destination = path.join(runRoot, logicalPath);
      mkdirSync(path.dirname(destination), { recursive: true });
      writeFileSync(destination, content);
      return {
        role,
        runId,
        logicalPath,
        sha256: digest(content),
        bytes: content.byteLength,
        mediaType: "application/json",
        claimLevel: "proxy",
      };
    });
    mkdirSync(path.join(runRoot, "data"), { recursive: true });
    writeFileSync(path.join(runRoot, "data", "roads.geojson"), roadsContent);
    writeFileSync(path.join(runRoot, "portfolio.sources.json"), sourceContent);
    const manifest = {
      schemaVersion: "portfolio-route-manifest/v1",
      runId,
      scenarioId: "abay-signal-retiming",
      claimLevel: "proxy",
      generatedAt: "2026-08-11T20:00:00Z",
      status: "promoted",
      sourceManifest: { path: "portfolio.sources.json", sha256: digest(sourceContent) },
      artifacts,
      aliases: {
        status: "synced",
        errors: [],
        paths: REQUIRED_PORTFOLIO_ARTIFACT_ROLES.map((role) => ({
          role,
          path: `aliases/${role}.json`,
        })),
      },
    };
    mkdirSync(path.dirname(currentPath), { recursive: true });
    writeFileSync(currentPath, JSON.stringify(manifest));
    writeFileSync(path.join(runRoot, "route-manifest.json"), JSON.stringify(manifest));
    const mutablePackPath = path.join(
      workspace,
      "reports",
      "akimat",
      "abay-signal-retiming",
      "procurement_pack_index.json",
    );
    mkdirSync(path.dirname(mutablePackPath), { recursive: true });
    writeFileSync(mutablePackPath, JSON.stringify({ marker: "mutable-alias-must-not-be-read" }));

    const loaded = await loadPromotedPortfolioRelease(workspace);
    assert.equal(loaded.manifest.runId, runId);
    assert.equal(loaded.sources.roadsGeojson.sha256, digest(roadsContent));
    assert.deepEqual(loaded.artifacts.procurementPack, artifactPayloads.procurementPack);

    const immutablePackPath = path.join(runRoot, "artifacts", "procurementPack.json");
    const immutablePackContent = Buffer.from(JSON.stringify(artifactPayloads.procurementPack));
    writeFileSync(immutablePackPath, JSON.stringify({ marker: "tampered-promoted-pack" }));
    await expectAsyncReleaseError(
      () => loadPromotedPortfolioRelease(workspace),
      "artifact_stale",
    );
    writeFileSync(immutablePackPath, immutablePackContent);
    const validRoadProvider = {
      id: "roads-geojson",
      available: true,
      claim_label: "real-data",
      path: "data/roads.geojson",
      sha256: digest(roadsContent),
      bytes: roadsContent.byteLength,
      feature_count: 0,
    };
    assert.equal(
      validateRoadProviderEvidence(
        { providers: [validRoadProvider] },
        loaded.sources.roadsGeojson,
        0,
      ).id,
      "roads-geojson",
    );
    assert.throws(
      () =>
        validateRoadProviderEvidence(
          { providers: [{ ...validRoadProvider, feature_count: 1 }] },
          loaded.sources.roadsGeojson,
          0,
        ),
      (error: unknown) => error instanceof PortfolioReleaseError && error.code === "artifact_stale",
    );
    assert.equal((await loadPromotedPortfolioRelease(workspace, runId)).manifest.runId, runId);
    await expectAsyncReleaseError(
      () => loadPromotedPortfolioRelease(workspace, "../unsafe"),
      "manifest_contract_invalid",
    );
    await expectAsyncReleaseError(
      () => loadPromotedPortfolioRelease(workspace, "portfolio-filesystem-404"),
      "manifest_missing",
    );

    writeFileSync(path.join(runRoot, "data", "roads.geojson"), "{}");
    await expectAsyncReleaseError(
      () => loadPromotedPortfolioRelease(workspace),
      "artifact_stale",
    );
    writeFileSync(path.join(runRoot, "data", "roads.geojson"), roadsContent);
    rmSync(path.join(runRoot, "data", "roads.geojson"));
    await expectAsyncReleaseError(
      () => loadPromotedPortfolioRelease(workspace),
      "artifact_missing",
    );
    writeFileSync(path.join(runRoot, "data", "roads.geojson"), roadsContent);

    const sourcePayload = JSON.parse(sourceContent.toString("utf8")) as {
      sources: Array<Record<string, unknown>>;
    };
    const duplicateSourceContent = Buffer.from(
      JSON.stringify({ ...sourcePayload, sources: [...sourcePayload.sources, { ...sourcePayload.sources[0] }] }),
    );
    writeFileSync(path.join(runRoot, "portfolio.sources.json"), duplicateSourceContent);
    manifest.sourceManifest.sha256 = digest(duplicateSourceContent);
    writeFileSync(currentPath, JSON.stringify(manifest));
    await expectAsyncReleaseError(
      () => loadPromotedPortfolioRelease(workspace),
      "manifest_contract_invalid",
    );

    const missingRuntimeSourceContent = Buffer.from(
      JSON.stringify({
        ...sourcePayload,
        sources: [{ ...sourcePayload.sources[0], role: "anotherSource", kind: "code", sha256: null }],
      }),
    );
    writeFileSync(path.join(runRoot, "portfolio.sources.json"), missingRuntimeSourceContent);
    manifest.sourceManifest.sha256 = digest(missingRuntimeSourceContent);
    writeFileSync(currentPath, JSON.stringify(manifest));
    await expectAsyncReleaseError(
      () => loadPromotedPortfolioRelease(workspace),
      "manifest_contract_invalid",
    );
    writeFileSync(path.join(runRoot, "portfolio.sources.json"), sourceContent);
    manifest.sourceManifest.sha256 = digest(sourceContent);
    writeFileSync(currentPath, JSON.stringify(manifest));

    writeFileSync(path.join(workspace, "portfolio.sources.json"), sourceContent);
    writeFileSync(path.join(runRoot, "portfolio.sources.json"), "{}");
    await expectAsyncReleaseError(
      () => loadPromotedPortfolioRelease(workspace),
      "artifact_stale",
    );
    writeFileSync(path.join(runRoot, "portfolio.sources.json"), sourceContent);

    const forgedDossier = Buffer.from(
      JSON.stringify({ trustMetadata: { runId: "portfolio-filesystem-002" } }),
    );
    writeFileSync(path.join(runRoot, "artifacts", "dossier.json"), forgedDossier);
    const dossierEntry = manifest.artifacts.find((artifact) => artifact.role === "dossier");
    assert.ok(dossierEntry);
    dossierEntry.sha256 = digest(forgedDossier);
    dossierEntry.bytes = forgedDossier.byteLength;
    writeFileSync(currentPath, JSON.stringify(manifest));
    await expectAsyncReleaseError(
      () => loadPromotedPortfolioRelease(workspace),
      "mixed_release",
    );

    const outside = mkdtempSync(path.join(tmpdir(), "almaty-route-outside-"));
    try {
      rmSync(path.join(workspace, "reports"), { recursive: true, force: true });
      mkdirSync(path.join(workspace, "reports"), { recursive: true });
      mkdirSync(path.join(outside, "portfolio", "runs"), { recursive: true });
      symlinkSync(path.join(outside, "portfolio"), path.join(workspace, "reports", "portfolio"));
      await expectAsyncReleaseError(
        () => loadPromotedPortfolioRelease(workspace),
        "manifest_path_invalid",
      );
    } finally {
      rmSync(outside, { recursive: true, force: true });
    }
  } finally {
    rmSync(workspace, { recursive: true, force: true });
  }
}

verifyImmutableFilesystemBindings()
  .then(() => {
    console.log(
      JSON.stringify({
        status: "passed",
        validFixture: parsed.runId,
        artifactRoles: parsed.artifacts.length,
        rejected: [
          "invalid fixture",
          "mixed release",
          "path traversal",
          "duplicate aliases",
          "materialized source tamper",
          "mutable procurement alias and immutable pack tamper",
          "required source tamper and deletion",
          "duplicate and missing runtime source records",
          "unsafe and unknown pinned run",
          "parent symlink escape",
          "rehashed nested mixed release",
        ],
        empiricalCalibrationGate: "passed",
      }),
    );
  })
  .catch((error) => {
    console.error(error);
    process.exitCode = 1;
  });
