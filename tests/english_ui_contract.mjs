import assert from "node:assert/strict";
import { readdirSync, readFileSync } from "node:fs";
import { join, relative } from "node:path";

const ROOT = process.cwd();
const CYRILLIC = /[\u0400-\u04ff]/;
const allowedCyrillicLookupLines = new Map([
  ["src/components/TrafficMap.tsx", [
    /id: "al-farabi", corridor: "Al-Farabi Ave", aliases: \["al-farabi", "аль-фараби", "al farabi"\]/,
    /id: "abay", corridor: "Abay Ave", aliases: \["abay", "абая"\]/,
    /id: "dostyk", corridor: "Dostyk Ave", aliases: \["dostyk", "достык"\]/,
  ]],
  ["src/components/dossier/AbayCorridorMap.tsx", [/return name\.includes\("абай"\) && feature\.geometry\.coordinates\.some\(isCoordinateInFocus\);/]],
]);

function filesUnder(directory) {
  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const path = join(directory, entry.name);
    return entry.isDirectory() ? filesUnder(path) : [path];
  });
}

for (const directory of ["src/app", "src/components"]) {
  for (const file of filesUnder(join(ROOT, directory)).filter((path) => /\.(ts|tsx|css)$/.test(path))) {
    const projectPath = relative(ROOT, file);
    const permittedPatterns = allowedCyrillicLookupLines.get(projectPath) ?? [];
    readFileSync(file, "utf8").split("\n").forEach((line, index) => {
      if (CYRILLIC.test(line)) {
        assert.ok(
          permittedPatterns.some((pattern) => pattern.test(line)),
          `Unexpected Cyrillic in ${projectPath}:${index + 1}`,
        );
      }
    });
  }
}

const layout = readFileSync(join(ROOT, "src/app/layout.tsx"), "utf8");
const home = readFileSync(join(ROOT, "src/app/page.tsx"), "utf8");
const sandbox = readFileSync(join(ROOT, "src/app/sandbox/page.tsx"), "utf8");
const nextConfig = readFileSync(join(ROOT, "next.config.ts"), "utf8");

assert.match(layout, /<html lang="en">/);
assert.match(home, /permanentRedirect\("\/scenarios\/abay-signal-retiming\/dossier"\)/);
assert.match(
  nextConfig,
  /source:\s*"\/"[\s\S]*destination:\s*"\/scenarios\/abay-signal-retiming\/dossier"[\s\S]*permanent:\s*true/,
);
assert.match(sandbox, /Interactive demo sandbox — uses demo and proxy data\./);
assert.match(sandbox, /It is not live traffic, calibrated evidence, or a funding recommendation\./);
assert.match(sandbox, /Open the evidence dossier/);

console.log("English UI source contract passed.");
