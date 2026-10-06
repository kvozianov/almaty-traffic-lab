import assert from "node:assert/strict";
import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import { AxeBuilder } from "@axe-core/playwright";
import { chromium, firefox, webkit } from "playwright";

const baseUrl = process.env.PORTFOLIO_URL ?? "http://127.0.0.1:3036";
const dossierPath = "/scenarios/abay-signal-retiming/dossier";
const dossierUrl = new URL(dossierPath, baseUrl).href;
const sandboxUrl = new URL("/sandbox", baseUrl).href;
const headless = process.env.PORTFOLIO_HEADLESS === "true" || process.env.CI === "true";
const qaOutputRoot = process.env.PORTFOLIO_QA_OUTPUT_DIR ?? "reports";
const uiOutputRoot = path.join(qaOutputRoot, "ui");
const qaReportPath = path.join(qaOutputRoot, "qa", "m3-browser-quality.json");
const report = {
  generatedAt: new Date().toISOString(),
  baseUrl,
  responsive: [],
  browsers: [],
  axe: [],
  privacy: {},
  metadata: {},
  print: {},
  screenshots: [],
};

const browserLaunches = [
  ["chromium", chromium, process.env.PORTFOLIO_CHROMIUM_EXECUTABLE],
  ["firefox", firefox, process.env.PORTFOLIO_FIREFOX_EXECUTABLE],
  ["webkit", webkit, process.env.PORTFOLIO_WEBKIT_EXECUTABLE],
];

async function withBrowser(name, browserType, executablePath, callback) {
  const browser = await browserType.launch({
    headless,
    ...(executablePath ? { executablePath } : {}),
  });
  try {
    return await callback(browser);
  } finally {
    await browser.close();
  }
}

async function inspectAxe(page, label) {
  const results = await new AxeBuilder({ page }).analyze();
  const blocking = results.violations.filter((violation) => ["serious", "critical"].includes(violation.impact));
  report.axe.push({ label, violationCount: results.violations.length, blocking });
  assert.equal(
    blocking.length,
    0,
    `${label} contains serious or critical axe violations: ${blocking.map((violation) => `${violation.id} (${violation.nodes.length})`).join(", ")}`,
  );
}

async function captureEvidenceScreenshot(page, filename, options = {}) {
  const outputPath = path.join(uiOutputRoot, filename);
  let lastError;
  for (let attempt = 1; attempt <= 3; attempt += 1) {
    try {
      await page.bringToFront();
      await page.waitForTimeout(attempt === 1 ? 0 : 250);
      await page.screenshot({ path: outputPath, animations: "disabled", scale: "css", ...options });
      report.screenshots.push({ filename, status: "captured", attempts: attempt });
      return;
    } catch (error) {
      lastError = error;
    }
  }

  report.screenshots.push({
    filename,
    status: "not-captured",
    attempts: 3,
    reason: lastError instanceof Error ? lastError.message : String(lastError),
  });
}

async function main() {
  const [chromiumName, chromiumType, chromiumExecutable] = browserLaunches[0];
  await withBrowser(chromiumName, chromiumType, chromiumExecutable, async (browser) => {
    await mkdir(uiOutputRoot, { recursive: true });
    for (const [label, width, height] of [
      ["mobile", 390, 844],
      ["tablet", 768, 1024],
      ["laptop", 1280, 720],
      ["desktop", 1440, 900],
    ]) {
      const context = await browser.newContext({ viewport: { width, height } });
      const page = await context.newPage();
      await page.goto(dossierUrl, { waitUntil: "networkidle" });
      const dossier = await page.evaluate(() => ({
        clientWidth: document.documentElement.clientWidth,
        h1Count: document.querySelectorAll("h1").length,
        scrollWidth: document.documentElement.scrollWidth,
        hasMain: Boolean(document.querySelector("main#main-content")),
        showsUnconditionalFunding: document.body.innerText.includes("Fund unconditionally"),
      }));
      assert.ok(dossier.scrollWidth <= dossier.clientWidth, `${label} dossier overflows horizontally`);
      assert.equal(dossier.h1Count, 1, `${label} dossier must have one h1`);
      assert.equal(dossier.hasMain, true, `${label} dossier must have a main landmark`);
      assert.equal(dossier.showsUnconditionalFunding, false, `${label} dossier must not expose unconditional funding`);
      if (label === "mobile" || label === "desktop") {
        await captureEvidenceScreenshot(page, `m3-dossier-${label}.png`);
      }

      await page.goto(sandboxUrl, { waitUntil: "networkidle" });
      const sandbox = await page.evaluate(() => ({
        clientWidth: document.documentElement.clientWidth,
        disclaimer: document.body.innerText.includes("Interactive demo sandbox — uses demo and proxy data."),
        fullDisclaimer: document.body.innerText.includes("It is not live traffic, calibrated evidence, or a funding recommendation."),
        mobileControlsOpen: document.querySelector("details[data-mobile-controls]")?.hasAttribute("open") ?? null,
        scrollWidth: document.documentElement.scrollWidth,
      }));
      assert.ok(sandbox.scrollWidth <= sandbox.clientWidth, `${label} sandbox overflows horizontally`);
      assert.equal(sandbox.disclaimer, true, `${label} sandbox disclaimer is missing`);
      assert.equal(sandbox.fullDisclaimer, true, `${label} sandbox full disclaimer is missing`);
      assert.notEqual(sandbox.mobileControlsOpen, null, `${label} sandbox mobile controls disclosure is missing`);
      assert.equal(
        sandbox.mobileControlsOpen,
        width > 720,
        `${label} sandbox controls must start ${width > 720 ? "open" : "closed"}`,
      );
      if (label === "mobile" || label === "desktop") {
        await captureEvidenceScreenshot(page, `m3-sandbox-${label}.png`);
      }
      if (width <= 720) {
        const summary = page.locator("details[data-mobile-controls] > summary");
        const summaryBox = await summary.boundingBox();
        assert.ok(summaryBox && summaryBox.height >= 44, `${label} sandbox controls summary must be at least 44px high`);
        await summary.click();
        assert.equal(
          await page.locator("details[data-mobile-controls]").evaluate((details) => details.open),
          true,
          `${label} sandbox controls must expand from the summary`,
        );
        const undersizedTargets = await page.locator("details[data-mobile-controls]").evaluate((details) =>
          [
            ...details.querySelectorAll("button, select, input[type='range'], label:has(input[type='checkbox'])"),
          ].flatMap((element) => {
            const box = element.getBoundingClientRect();
            return box.width >= 44 && box.height >= 44
              ? []
              : [{ label: element.textContent?.trim() || element.getAttribute("aria-label") || element.tagName, width: box.width, height: box.height }];
          }),
        );
        assert.deepEqual(undersizedTargets, [], `${label} sandbox contains undersized controls: ${JSON.stringify(undersizedTargets)}`);
      }
      report.responsive.push({ label, width, height, dossier, sandbox });
      await context.close();
    }

    const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
    const page = await context.newPage();
    const requestedHosts = new Set();
    page.on("request", (request) => requestedHosts.add(new URL(request.url()).host));
    await page.goto(dossierUrl, { waitUntil: "networkidle" });
    await inspectAxe(page, "dossier");

    await page.keyboard.press("Tab");
    const skipLinkFocused = await page.locator('a[href="#main-content"]').evaluate((element) => document.activeElement === element);
    assert.equal(skipLinkFocused, true, "Skip link must receive the first keyboard focus");
    await page.keyboard.press("Enter");
    assert.equal(await page.locator("#main-content").evaluate((element) => document.activeElement === element), true, "Skip link must move focus to main content");

    const metadata = await page.evaluate(() => ({
      canonical: document.querySelector('link[rel="canonical"]')?.getAttribute("href"),
      description: document.querySelector('meta[name="description"]')?.getAttribute("content"),
      ogImage: document.querySelector('meta[property="og:image"]')?.getAttribute("content"),
      robots: document.querySelector('meta[name="robots"]')?.getAttribute("content"),
      structuredData: document.querySelector('script[type="application/ld+json"]')?.textContent,
      title: document.title,
    }));
    assert.equal(metadata.canonical, dossierPath, "Canonical path must target the dossier");
    assert.match(metadata.title, /Abay Avenue signal-retiming case/);
    assert.match(metadata.description ?? "", /proxy case dossier/i);
    assert.match(metadata.ogImage ?? "", /opengraph-image/);
    assert.match(metadata.robots ?? "", /noindex/);
    assert.equal(JSON.parse(metadata.structuredData ?? "{}")["@type"], "CreativeWork");
    report.metadata = metadata;

    await page.emulateMedia({ media: "print" });
    const printVisibility = await page.evaluate(() => ({
      downloadsVisible: getComputedStyle(document.querySelector("[data-print-hidden]"))?.display !== "none",
      dossierTextVisible: document.body.innerText.includes("Decision workbench"),
      headerVisible: getComputedStyle(document.querySelector(".site-header"))?.display !== "none",
    }));
    assert.equal(printVisibility.downloadsVisible, false, "Print output must not contain interactive downloads");
    assert.equal(printVisibility.headerVisible, false, "Print output must not contain site navigation");
    assert.equal(printVisibility.dossierTextVisible, true, "Print output must retain the evidence dossier");
    await mkdir(uiOutputRoot, { recursive: true });
    await captureEvidenceScreenshot(page, "m3-dossier-print.png", { fullPage: true });
    await page.pdf({ path: path.join(uiOutputRoot, "m3-dossier-print.pdf"), printBackground: true, preferCSSPageSize: true });
    report.print = printVisibility;

    const dossierCookies = await context.cookies();
    const dossierStorage = await page.evaluate(() => ({ localStorage: localStorage.length, sessionStorage: sessionStorage.length }));
    const dossierExternalHosts = [...requestedHosts].filter((host) => host && host !== new URL(baseUrl).host);
    report.privacy = { dossierCookies: dossierCookies.length, dossierStorage, dossierHosts: [new URL(baseUrl).host], dossierExternalHosts };
    assert.equal(dossierCookies.length, 0, "Dossier must not set tracking cookies");
    assert.deepEqual(dossierStorage, { localStorage: 0, sessionStorage: 0 }, "Dossier must not persist browser storage");
    assert.deepEqual(dossierExternalHosts, [], `Dossier must not request external providers: ${dossierExternalHosts.join(", ")}`);

    requestedHosts.clear();
    await page.emulateMedia({ media: "screen" });
    await page.goto(sandboxUrl, { waitUntil: "networkidle" });
    await inspectAxe(page, "sandbox");
    const externalHosts = [...requestedHosts].filter((host) => host && host !== new URL(baseUrl).host);
    assert.ok(externalHosts.every((host) => /(^|\.)cartocdn\.com$/.test(host)), `Unexpected sandbox external hosts: ${externalHosts.join(", ")}`);
    report.privacy = { ...report.privacy, sandboxExternalHosts: externalHosts };
    await context.close();
  });

  for (const [name, browserType, executablePath] of browserLaunches) {
    await withBrowser(name, browserType, executablePath, async (browser) => {
      const context = await browser.newContext({ viewport: { width: 1280, height: 720 } });
      const page = await context.newPage();
      const pageErrors = [];
      const consoleErrors = [];
      const requestFailures = [];
      page.on("pageerror", (error) => pageErrors.push(error.message));
      page.on("console", (message) => {
        if (message.type() === "error") consoleErrors.push(message.text());
      });
      page.on("requestfailed", (request) => {
        requestFailures.push(`${request.method()} ${request.url()} · ${request.failure()?.errorText ?? "unknown"}`);
      });
      await page.goto(dossierUrl, { waitUntil: "networkidle" });
      const result = await page.evaluate(() => ({ h1Count: document.querySelectorAll("h1").length, main: Boolean(document.querySelector("main#main-content")) }));
      assert.equal(result.h1Count, 1, `${name} dossier h1 count`);
      assert.equal(result.main, true, `${name} dossier main landmark`);
      assert.deepEqual(pageErrors, [], `${name} page errors`);
      assert.deepEqual(consoleErrors, [], `${name} console errors`);
      const unexpectedRequestFailures = requestFailures.filter((failure) => !failure.endsWith("net::ERR_ABORTED"));
      assert.deepEqual(unexpectedRequestFailures, [], `${name} request failures`);
      report.browsers.push({
        name,
        ...result,
        pageErrors,
        consoleErrors,
        requestFailures,
        unexpectedRequestFailures,
      });
      await context.close();
    });
  }

  const requiredScreenshots = [
    "m3-dossier-desktop.png",
    "m3-dossier-mobile.png",
    "m3-dossier-print.png",
    "m3-sandbox-desktop.png",
    "m3-sandbox-mobile.png",
  ];
  const capturedScreenshots = report.screenshots
    .filter((item) => item.status === "captured")
    .map((item) => item.filename)
    .sort();
  assert.deepEqual(capturedScreenshots, requiredScreenshots.sort(), "Every required QA screenshot must be captured");

  await mkdir(path.dirname(qaReportPath), { recursive: true });
  await writeFile(qaReportPath, `${JSON.stringify(report, null, 2)}\n`);
}

try {
  await main();
} catch (error) {
  report.error = error instanceof Error ? error.message : String(error);
  await mkdir(path.dirname(qaReportPath), { recursive: true });
  await writeFile(qaReportPath, `${JSON.stringify(report, null, 2)}\n`);
  throw error;
}
