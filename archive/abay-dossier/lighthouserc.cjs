/**
 * This configuration is executed only by the digest-pinned Playwright CI image
 * recorded in security-tools.lock.json. The M5 runner performs two warm-ups
 * before invoking this five-run measured collection.
 */
module.exports = {
  ci: {
    collect: {
      numberOfRuns: 5,
      startServerCommand: "PORT=3036 npm run start",
      startServerReadyPattern: "Ready",
      startServerReadyTimeout: 30_000,
      url: ["http://127.0.0.1:3036/scenarios/abay-signal-retiming/dossier"],
      settings: {
        chromeFlags: "--headless=new --no-sandbox",
        formFactor: "mobile",
        screenEmulation: {
          mobile: true,
          width: 390,
          height: 844,
          deviceScaleFactor: 1,
          disabled: false,
        },
        throttlingMethod: "simulate",
        throttling: {
          rttMs: 150,
          throughputKbps: 1600,
          cpuSlowdownMultiplier: 4,
          requestLatencyMs: 150,
          downloadThroughputKbps: 1600,
          uploadThroughputKbps: 750,
        },
      },
    },
    assert: {
      assertions: {
        "categories:performance": ["error", { minScore: 0.9 }],
        "largest-contentful-paint": ["error", { maxNumericValue: 2500 }],
        "cumulative-layout-shift": ["error", { maxNumericValue: 0.1 }],
        "resource-summary:script:size": ["error", { maxNumericValue: 358400 }],
      },
    },
    upload: {
      target: "filesystem",
      outputDir: "reports/performance/v0.1.0",
    },
  },
};
