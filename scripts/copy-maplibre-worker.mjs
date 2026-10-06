// MapLibre GL 6 loads its web worker from a separate ES module next to the
// library. Bundlers do not emit it, so we serve the published files from
// public/vendor and point MapLibre at them with setWorkerUrl().
import { copyFileSync, mkdirSync, readFileSync } from "node:fs";

const src = "node_modules/maplibre-gl/dist";
const dest = "public/vendor/maplibre";
const { version } = JSON.parse(readFileSync("node_modules/maplibre-gl/package.json", "utf8"));
mkdirSync(dest, { recursive: true });
for (const file of ["maplibre-gl-worker.mjs", "maplibre-gl-shared.mjs"]) copyFileSync(`${src}/${file}`, `${dest}/${file}`);
console.log(`maplibre-gl ${version} worker copied to ${dest}`);
