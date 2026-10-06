/**
 * Captures the README screenshots from a running production build.
 *   BASE_URL=http://localhost:3100 node scripts/screenshots.mjs
 */
import { chromium } from "playwright";

const BASE = process.env.BASE_URL ?? "http://localhost:3100";
const OUT = "docs/assets";
const browser = await chromium.launch();
const context = await browser.newContext({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 2 });
const page = await context.newPage();

await page.goto(`${BASE}/lab?example=abay-repairs`);
await page.getByText("Where traffic moved").waitFor({ timeout: 60_000 });
await page.waitForTimeout(2500); // map tiles and fly-to animation
await page.screenshot({ path: `${OUT}/lab-result.png` });

await page.goto(`${BASE}/lab`);
await page.getByText("Traffic load").waitFor();
await page.waitForTimeout(3000);
await page.screenshot({ path: `${OUT}/lab-baseline.png` });

await page.goto(`${BASE}/`);
await page.waitForTimeout(3000);
await page.screenshot({ path: `${OUT}/home.png` });

const phone = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 3, isMobile: true });
const p = await phone.newPage();
await p.goto(`${BASE}/lab?example=tole-bi-bus-lane`);
await p.getByText("Where traffic moved").waitFor({ timeout: 60_000 });
await p.waitForTimeout(2500);
await p.screenshot({ path: `${OUT}/lab-phone.png` });

await browser.close();
console.log("screenshots written to", OUT);
// README uses JPEG copies: `sips -s format jpeg -s formatOptions 82 x.png --out x.jpg` (macOS).
