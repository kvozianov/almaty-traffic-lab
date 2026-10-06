import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";

const root = process.cwd();
const read = (relativePath) => readFileSync(path.join(root, relativePath), "utf8");
const cyrillic = /[\u0400-\u04ff]/;

const requiredDocuments = [
  "README.md",
  "README_METHODS.md",
  "README_VALIDATION.md",
  "docs/ARCHITECTURE.md",
  "docs/DEMO_SCRIPT.md",
  "docs/PORTFOLIO_CASE.md",
];
for (const document of requiredDocuments) {
  const content = read(document);
  assert.ok(content.length > 200, `${document} must contain a substantive English release draft`);
  assert.equal(cyrillic.test(content), false, `${document} must not contain Cyrillic public copy`);
}

const current = JSON.parse(read("reports/portfolio/current.json"));
const dossier = JSON.parse(
  read(path.join("reports/portfolio/runs", current.runId, "reports/dossiers/abay-signal-retiming/dossier.json")),
);
const readme = read("README.md");
const values = new Map((dossier.executiveKpis.kpis).map((kpi) => [kpi.id, kpi]));
for (const id of ["person_hours", "corridor_speed_delta", "queue_load_proxy", "co2_proxy", "roi_proxy"]) {
  const kpi = values.get(id);
  assert.ok(kpi, `promoted dossier must include ${id}`);
  assert.ok(readme.includes(String(kpi.baseline)), `README must source ${id} baseline from the promoted dossier`);
  assert.ok(readme.includes(String(kpi.measure)), `README must source ${id} measure from the promoted dossier`);
  assert.ok(readme.includes(String(kpi.delta)), `README must source ${id} delta from the promoted dossier`);
}
assert.match(readme, /Current evidence boundary:.*`proxy`/s);
assert.match(readme, /docs\/ARCHITECTURE\.md/);
assert.match(readme, /docs\/DEMO_SCRIPT\.md/);
assert.match(read("docs/DEMO_SCRIPT.md"), /scenario configuration → controlled pair → KPI\/evidence JSON → immutable release/i);
assert.match(read("docs/ARCHITECTURE.md"), /Production GET routes are read-only/i);
assert.match(read("docs/PORTFOLIO_CASE.md"), /not claimed: field calibration/i);

console.log("Documentation contract passed.");
