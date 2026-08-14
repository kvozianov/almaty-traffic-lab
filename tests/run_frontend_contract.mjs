import { mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const workspace = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const output = mkdtempSync(path.join(tmpdir(), "almaty-frontend-contract-"));

function run(command, args) {
  const result = spawnSync(command, args, { cwd: workspace, stdio: "inherit" });
  if (result.error) throw result.error;
  if (result.status !== 0) process.exitCode = result.status ?? 1;
  return result.status === 0;
}

try {
  const compiled = run(process.execPath, [
    path.join(workspace, "node_modules", "typescript", "bin", "tsc"),
    "--ignoreConfig",
    "tests/portfolio_route_manifest_contract.ts",
    "src/components/dossier/evidence.ts",
    "src/components/dossier/generationBoundary.ts",
    "src/components/dossier/portfolioRelease.ts",
    "src/components/dossier/types.ts",
    "--outDir",
    output,
    "--rootDir",
    ".",
    "--module",
    "Node16",
    "--target",
    "ES2022",
    "--moduleResolution",
    "Node16",
    "--esModuleInterop",
    "--skipLibCheck",
    "--types",
    "node",
    "--noEmitOnError",
  ]);

  if (compiled) {
    run(process.execPath, [path.join(output, "tests", "portfolio_route_manifest_contract.js")]);
  }
} finally {
  rmSync(output, { recursive: true, force: true });
}
