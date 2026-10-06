import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import path from "node:path";

const ROOT = process.cwd();
const EXPECTED_IDS = [
  "dossier-html",
  "dossier-json",
  "kpis-csv",
  "run-passport-json",
  "procurement-index-json",
];
const CYRILLIC = /[\u0400-\u04ff]/;
const current = JSON.parse(readFileSync(path.join(ROOT, "reports/portfolio/current.json"), "utf8"));

assert.equal(current.status, "promoted");
assert.deepEqual(current.downloads.map((download) => download.id), EXPECTED_IDS);

for (const download of current.downloads) {
  assert.equal(download.runId, current.runId, `${download.id} must belong to the promoted run`);
  assert.match(download.logicalPath, /^(?!\/)(?!.*(?:^|\/)\.\.(?:\/|$)).+$/);
  assert.match(download.filename, /^[A-Za-z0-9][A-Za-z0-9._-]*$/);
  const artifactPath = path.resolve(ROOT, "reports/portfolio/runs", current.runId, download.logicalPath);
  const content = readFileSync(artifactPath);
  assert.ok(content.byteLength > 0, `${download.id} must not be empty`);
  assert.equal(content.byteLength, download.bytes, `${download.id} bytes must match`);
  assert.equal(createHash("sha256").update(content).digest("hex"), download.sha256, `${download.id} hash must match`);
  assert.equal(CYRILLIC.test(content.toString("utf8")), false, `${download.id} must be English-only`);
}

const html = readFileSync(
  path.join(ROOT, "reports/portfolio/runs", current.runId, "reports/dossiers/abay-signal-retiming/dossier.html"),
  "utf8",
);
const csv = readFileSync(
  path.join(ROOT, "reports/portfolio/runs", current.runId, "reports/dossiers/abay-signal-retiming/kpis.csv"),
  "utf8",
);
assert.match(html, /<html lang="en">/i);
assert.match(csv, /^id,label,unit,baseline,measure,delta,direction,claimLevel,formula,placeholder,available/m);

console.log("Portfolio download contract passed.");
