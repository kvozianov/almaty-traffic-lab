/**
 * End-to-end check of the path an admissions reviewer takes:
 * home → example question → result → full report, on desktop and phone,
 * plus an axe accessibility scan of every page.
 *
 *   npm run build && npm run start -- -p 3100 &
 *   BASE_URL=http://localhost:3100 node tests/e2e/visitor-flow.mjs
 */
import assert from "node:assert/strict";
import AxeBuilder from "@axe-core/playwright";
import { chromium } from "playwright";

const BASE = process.env.BASE_URL ?? "http://localhost:3100";
const browser = await chromium.launch();
const failures = [];

async function step(name, fn) {
  const started = Date.now();
  try {
    await fn();
    console.log(`✓ ${name} (${Date.now() - started} ms)`);
  } catch (error) {
    failures.push(name);
    console.error(`✗ ${name}\n  ${error instanceof Error ? error.message : error}`);
  }
}

async function noSeriousA11yIssues(page, label) {
  const { violations } = await new AxeBuilder({ page }).exclude(".maplibregl-canvas").analyze();
  const serious = violations.filter((v) => v.impact === "serious" || v.impact === "critical");
  assert.equal(serious.length, 0, `${label}: ${serious.map((v) => `${v.id} (${v.nodes.length})`).join(", ")}`);
}

for (const device of [
  { name: "desktop", viewport: { width: 1440, height: 900 } },
  { name: "phone", viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true },
]) {
  const context = await browser.newContext({ viewport: device.viewport, isMobile: device.isMobile, hasTouch: device.hasTouch });
  const page = await context.newPage();
  const errors = [];
  page.on("pageerror", (e) => errors.push(e.message));

  await step(`${device.name}: home page explains the project and shows the city`, async () => {
    await page.goto(`${BASE}/`);
    await page.getByRole("heading", { level: 1, name: /What happens to Almaty traffic/ }).waitFor();
    await page.getByText(/car trips/).first().waitFor();
    await noSeriousA11yIssues(page, "home");
  });

  await step(`${device.name}: an example question runs and explains its result`, async () => {
    await page.getByRole("link", { name: /Abay Avenue closes for repairs/ }).click();
    await page.waitForURL(/\/lab/);
    const headline = page.getByRole("heading", { level: 2, name: /Abay Avenue/ });
    await headline.waitFor({ timeout: 30_000 });
    assert.match(await headline.innerText(), /average morning trip/);
    await page.getByText("Where traffic moved").waitFor();
    assert.match(page.url(), /[?&]s=/, "scenario is kept in the URL");
    // Streets that changed are labelled on the map and can be pinned from the list.
    const pills = page.locator(".maplibregl-marker button");
    assert.ok((await pills.count()) >= 3, "affected streets are labelled on the map");
    // First row of "Where traffic moved" (rows are toggle buttons showing a percentage).
    const row = page.locator("button[aria-pressed]").filter({ hasText: "%" }).first();
    await row.click();
    assert.equal(await row.getAttribute("aria-pressed"), "true");
    const toggle = page.getByRole("button", { name: /moving traffic|Traffic moving/ });
    assert.equal(await toggle.getAttribute("aria-pressed"), "true", "traffic animation is on by default");
    await noSeriousA11yIssues(page, "lab result");
  });

  await step(`${device.name}: the full report reproduces the run with a passport`, async () => {
    await page.getByRole("link", { name: /Full report/ }).click();
    await page.getByText("05 · Run passport").waitFor({ timeout: 30_000 });
    const hash = await page.locator("dt", { hasText: "Result hash" }).locator("xpath=following-sibling::dd").innerText();
    assert.match(hash, /^[0-9a-f]{64}$/);
    await noSeriousA11yIssues(page, "report");
  });

  await step(`${device.name}: a street can be found, changed and re-routed`, async () => {
    await page.goto(`${BASE}/lab`);
    await page.getByRole("combobox").fill("tole bi");
    await page.getByRole("option").first().click();
    await page.getByRole("button", { name: /Close for repairs/ }).click();
    await page.getByRole("button", { name: "See what happens" }).click();
    await page.getByText("Where traffic moved").waitFor({ timeout: 30_000 });
  });

  await step(`${device.name}: the methods page is readable`, async () => {
    await page.goto(`${BASE}/methods`);
    await page.getByRole("heading", { name: /Every driver takes the fastest route/ }).waitFor();
    await noSeriousA11yIssues(page, "methods");
  });

  await step(`${device.name}: no uncaught page errors`, async () => {
    assert.deepEqual(errors, []);
  });
  await context.close();
}

await browser.close();
if (failures.length > 0) {
  console.error(`\n${failures.length} step(s) failed`);
  process.exit(1);
}
console.log("\nAll visitor-flow checks passed");
