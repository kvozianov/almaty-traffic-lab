import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { buildTripTrailSegments } from "../src/components/tripTrail.mjs";

const projectRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const mapSource = fs.readFileSync(path.join(projectRoot, "src/components/TrafficMap.tsx"), "utf8");

const trip = {
  path: [
    [0, 0],
    [10, 0],
    [20, 0],
  ],
  timestamps: [0, 10, 20],
};

const earlyFrame = buildTripTrailSegments([trip], 5, 4);
assert.equal(earlyFrame.length, 1, "Only the active first route segment should be visible");
assert.deepEqual(earlyFrame[0].path, [
  [1, 0],
  [5, 0],
]);

const laterFrame = buildTripTrailSegments([trip], 15, 4);
assert.equal(laterFrame.length, 1, "The expired first route segment must leave the trail window");
assert.deepEqual(laterFrame[0].path, [
  [11, 0],
  [15, 0],
]);
assert.notDeepEqual(laterFrame[0].path, earlyFrame[0].path, "currentTime must change visible route geometry");

const boundaryFrame = buildTripTrailSegments([trip], 12, 5);
assert.deepEqual(
  boundaryFrame.map((segment) => segment.path),
  [
    [
      [7, 0],
      [10, 0],
    ],
    [
      [10, 0],
      [12, 0],
    ],
  ],
  "The trail must interpolate both the window start and current-time head across timestamp boundaries",
);
assert.ok(
  boundaryFrame[0].opacity < boundaryFrame[1].opacity,
  "Older route segments should fade behind the current-time head",
);

assert.match(
  mapSource,
  /buildTripTrailSegments\(data, currentTime, trailLength\)/,
  "TrafficMap must pass animation time into the visible-route builder",
);
assert.match(
  mapSource,
  /\[currentTime, deckLayerNamespace, showAgentClasses/,
  "Deck route layers must be recomputed for each animation time",
);

console.log("Trip trail animation contract passed");
