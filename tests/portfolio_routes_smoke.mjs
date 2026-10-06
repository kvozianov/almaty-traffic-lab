import { strict as assert } from "node:assert";

const baseUrl = (process.env.PORTFOLIO_SMOKE_URL || "http://localhost:3036").replace(/\/$/, "");
const mode = process.env.PORTFOLIO_SMOKE_MODE || "production";
const allowGeneration = process.env.PORTFOLIO_SMOKE_ALLOW_GENERATION === "1";

assert.ok(["production", "developer"].includes(mode), "PORTFOLIO_SMOKE_MODE must be production or developer");

const results = [];
let promotedRunId = "";
let promotedSourceManifestSha = "";

async function expectJson(name, path, init, expectedStatus, verify = () => {}) {
  const response = await fetch(`${baseUrl}${path}`, init);
  const body = await response.json();
  assert.equal(response.status, expectedStatus, `${name}: ${JSON.stringify(body)}`);
  await verify(body, response);
  results.push({ name, status: response.status });
  return body;
}

async function expectDownload(id, mediaType, filename) {
  const response = await fetch(
    `${baseUrl}/api/downloads/${id}?runId=${encodeURIComponent(promotedRunId)}`,
  );
  const content = new Uint8Array(await response.arrayBuffer());
  assert.equal(response.status, 200, `${id}: ${new TextDecoder().decode(content)}`);
  assert.ok(content.byteLength > 0, `${id} must not return an empty body`);
  assert.match(response.headers.get("content-type") || "", new RegExp(`^${mediaType}`));
  assert.equal(response.headers.get("content-disposition"), `attachment; filename="${filename}"`);
  assert.equal(response.headers.get("x-content-type-options"), "nosniff");
  assert.equal(response.headers.get("x-portfolio-run-id"), promotedRunId);
  assert.equal(response.headers.get("x-portfolio-source-manifest-sha"), promotedSourceManifestSha);
  assert.equal(response.headers.get("x-portfolio-download-id"), id);
  assert.match(response.headers.get("x-portfolio-artifact-sha256") || "", /^[a-f0-9]{64}$/);
  assert.match(response.headers.get("cache-control") || "", /immutable/);
  results.push({ name: `GET download ${id}`, status: response.status });
}

await expectJson("GET promoted dossier", "/api/dossier", undefined, 200, (body, response) => {
  assert.equal(body.id, "abay-signal-retiming");
  promotedRunId = response.headers.get("x-portfolio-run-id") || "";
  promotedSourceManifestSha = response.headers.get("x-portfolio-source-manifest-sha") || "";
  assert.match(promotedRunId, /^[A-Za-z0-9][A-Za-z0-9._-]+$/);
  assert.match(promotedSourceManifestSha, /^[a-f0-9]{64}$/);
  assert.match(response.headers.get("cache-control") || "", /no-store/);
});

await expectJson(
  "GET promoted procurement pack",
  "/api/exports/procurement-pack",
  undefined,
  200,
  (body, response) => {
    assert.equal(body.id, "abay-signal-retiming-procurement-pilot-pack");
    assert.equal(body.scenarioId, "abay-signal-retiming");
    assert.equal(body.claimLevel, "demo");
    assert.equal(response.headers.get("x-portfolio-run-id"), promotedRunId);
    assert.equal(
      response.headers.get("x-portfolio-source-manifest-sha"),
      promotedSourceManifestSha,
    );
    assert.match(response.headers.get("cache-control") || "", /no-store/);
  },
);

for (const [id, mediaType, filename] of [
  ["dossier-html", "text/html", "abay-signal-retiming-dossier.html"],
  ["dossier-json", "application/json", "abay-signal-retiming-evidence.json"],
  ["kpis-csv", "text/csv", "abay-signal-retiming-kpis.csv"],
  ["run-passport-json", "application/json", "abay-signal-retiming-run-passport.json"],
  ["procurement-index-json", "application/json", "abay-signal-retiming-procurement-index.json"],
]) {
  await expectDownload(id, mediaType, filename);
}

await expectJson(
  "GET unknown download fails closed",
  `/api/downloads/not-an-artifact?runId=${encodeURIComponent(promotedRunId)}`,
  undefined,
  404,
  (body) => assert.equal(body.code, "download_not_found"),
);
await expectJson(
  "GET download rejects unsafe pinned run",
  "/api/downloads/dossier-html?runId=..%2Fescape",
  undefined,
  400,
  (body) => assert.equal(body.code, "manifest_contract_invalid"),
);

await expectJson(
  "GET pinned immutable roads",
  `/api/roads?runId=${encodeURIComponent(promotedRunId)}`,
  undefined,
  200,
  (body, response) => {
    assert.equal(body.type, "FeatureCollection");
    assert.ok(Array.isArray(body.features));
    assert.equal(body.providerStatus.id, "roads-geojson");
    assert.equal(body.providerStatus.available, true);
    assert.equal(body.providerStatus.claim_label, "real-data");
    assert.equal(body.providerStatus.feature_count, body.features.length);
    assert.equal(response.headers.get("x-portfolio-run-id"), promotedRunId);
    assert.match(response.headers.get("x-portfolio-source-sha256") || "", /^[a-f0-9]{64}$/);
    assert.equal(body.providerStatus.sha256, response.headers.get("x-portfolio-source-sha256"));
  },
);

await expectJson(
  "GET roads rejects unsafe pinned run",
  "/api/roads?runId=..%2Fescape",
  undefined,
  400,
  (body) => assert.equal(body.code, "manifest_contract_invalid"),
);
await expectJson(
  "GET roads rejects unknown pinned run",
  "/api/roads?runId=portfolio-smoke-missing",
  undefined,
  404,
  (body) => assert.equal(body.code, "manifest_missing"),
);

const pageResponse = await fetch(`${baseUrl}/scenarios/abay-signal-retiming/dossier`);
const pageHtml = await pageResponse.text();
assert.equal(pageResponse.status, 200, pageHtml.slice(0, 500));
assert.match(pageHtml, /Abay|Абая/);
for (const label of [
  "Download HTML dossier",
  "Download JSON evidence",
  "Download KPI CSV",
  "Download run passport",
  "Download procurement index",
  "Print / save as PDF",
]) {
  assert.match(pageHtml, new RegExp(label));
}
results.push({ name: "GET dossier page", status: pageResponse.status });

const validBody = JSON.stringify({ scenarioId: "abay-signal-retiming" });

if (mode === "production") {
  await expectJson(
    "POST hidden in production",
    "/api/dossiers",
    { method: "POST", headers: { "content-type": "application/json" }, body: validBody },
    404,
    (body) => assert.equal(body.error, "Not found."),
  );
  await expectJson(
    "POST procurement export hidden in production",
    "/api/exports/procurement-pack",
    { method: "POST", headers: { "content-type": "application/json" }, body: validBody },
    404,
    (body, response) => {
      assert.equal(body.error, "Not found.");
      assert.match(response.headers.get("cache-control") || "", /no-store/);
    },
  );
} else {
  await expectJson(
    "POST rejects content type",
    "/api/dossiers",
    { method: "POST", headers: { "content-type": "text/plain" }, body: validBody },
    415,
    (body) => assert.equal(body.code, "content_type_invalid"),
  );
  await expectJson(
    "POST rejects extra fields",
    "/api/dossiers",
    {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ scenarioId: "abay-signal-retiming", extra: true }),
    },
    400,
    (body) => assert.equal(body.code, "body_contract_invalid"),
  );
  await expectJson(
    "POST rejects unknown scenario",
    "/api/dossiers",
    {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ scenarioId: "another-scenario" }),
    },
    400,
    (body) => assert.equal(body.code, "scenario_not_allowed"),
  );
  await expectJson(
    "POST rejects path-like scenario",
    "/api/dossiers",
    {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ scenarioId: "../abay-signal-retiming" }),
    },
    400,
    (body) => assert.equal(body.code, "scenario_not_allowed"),
  );
  await expectJson(
    "POST rejects malformed JSON",
    "/api/dossiers",
    { method: "POST", headers: { "content-type": "application/json" }, body: "{" },
    400,
    (body) => assert.equal(body.code, "json_invalid"),
  );
  await expectJson(
    "POST rejects oversized body",
    "/api/dossiers",
    { method: "POST", headers: { "content-type": "application/json" }, body: `{"padding":"${"x".repeat(1100)}"}` },
    413,
    (body) => assert.equal(body.code, "body_too_large"),
  );

  await expectJson(
    "POST procurement rejects content type",
    "/api/exports/procurement-pack",
    { method: "POST", headers: { "content-type": "text/plain" }, body: validBody },
    415,
    (body) => assert.equal(body.code, "content_type_invalid"),
  );
  await expectJson(
    "POST procurement rejects extra fields",
    "/api/exports/procurement-pack",
    {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ scenarioId: "abay-signal-retiming", extra: true }),
    },
    400,
    (body) => assert.equal(body.code, "body_contract_invalid"),
  );
  await expectJson(
    "POST procurement rejects unsafe scenario",
    "/api/exports/procurement-pack",
    {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ scenarioId: "../abay-signal-retiming" }),
    },
    400,
    (body) => assert.equal(body.code, "scenario_not_allowed"),
  );
  await expectJson(
    "POST procurement rejects oversized body",
    "/api/exports/procurement-pack",
    {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: `{"padding":"${"x".repeat(1100)}"}`,
    },
    413,
    (body) => assert.equal(body.code, "body_too_large"),
  );

  if (allowGeneration) {
    await expectJson(
      "POST procurement promotes a verified release",
      "/api/exports/procurement-pack",
      { method: "POST", headers: { "content-type": "application/json" }, body: validBody },
      201,
      (body, response) => {
        assert.equal(body.manifest.status, "promoted");
        assert.equal(body.manifest.scenarioId, "abay-signal-retiming");
        assert.equal(body.procurementPack.scenarioId, "abay-signal-retiming");
        assert.equal(body.procurementPack.claimLevel, "demo");
        assert.ok(
          ["promoted", "promoted_with_alias_error", "promoted_with_warning"].includes(
            body.generation.status,
          ),
        );
        assert.equal(response.headers.get("x-portfolio-run-id"), body.manifest.runId);
        assert.equal(
          response.headers.get("x-portfolio-source-manifest-sha"),
          body.manifest.sourceManifest.sha256,
        );
        assert.match(response.headers.get("cache-control") || "", /no-store/);
      },
    );
  }
}

console.log(JSON.stringify({ status: "passed", mode, allowGeneration, results }));
