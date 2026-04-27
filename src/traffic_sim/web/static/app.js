const state = {
  map: null,
  roadsLayer: null,
  vehicleLayer: null,
  frames: [],
  baselineFrames: [],
  frameIndex: 0,
  animationId: null,
  lastTimestamp: null,
  frameProgressMs: 0,
  playing: true,
  selectedRoadId: null,
  currentRunId: null,
  vehicleMarkers: new Map(),
};

const els = {
  preset: document.getElementById("presetSelect"),
  vehicles: document.getElementById("vehicleInput"),
  steps: document.getElementById("stepsInput"),
  seed: document.getElementById("seedInput"),
  speed: document.getElementById("speedInput"),
  scenario: document.getElementById("scenarioSelect"),
  compare: document.getElementById("compareInput"),
  selectedRoad: document.getElementById("selectedRoad"),
  run: document.getElementById("runButton"),
  quick: document.getElementById("quickButton"),
  play: document.getElementById("playButton"),
  reset: document.getElementById("resetButton"),
  status: document.getElementById("mapStatus"),
  tick: document.getElementById("tickMetric"),
  moving: document.getElementById("movingMetric"),
  arrived: document.getElementById("arrivedMetric"),
  trip: document.getElementById("tripMetric"),
  load: document.getElementById("loadMetric"),
  delta: document.getElementById("deltaMetric"),
  hotRoads: document.getElementById("hotRoads"),
  exportMetrics: document.getElementById("exportMetrics"),
  exportRoads: document.getElementById("exportRoads"),
};

boot();

async function boot() {
  state.map = L.map("map", { zoomControl: false }).setView([43.238, 76.945], 12);
  L.control.zoom({ position: "bottomright" }).addTo(state.map);
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: "&copy; OpenStreetMap contributors",
  }).addTo(state.map);
  state.roadsLayer = L.layerGroup().addTo(state.map);
  state.vehicleLayer = L.layerGroup().addTo(state.map);

  await loadPresets();
  bindEvents();
  setStatus("Choose a preset, then press Run. Use Quick for a fast city-wide preview.");
}

async function loadPresets() {
  const response = await fetch("/api/presets");
  const data = await response.json();
  els.preset.innerHTML = "";
  for (const preset of data.presets) {
    const option = document.createElement("option");
    option.value = preset.id;
    option.textContent = preset.name;
    option.dataset.center = JSON.stringify(preset.center);
    option.dataset.zoom = preset.zoom;
    els.preset.appendChild(option);
  }
  els.preset.value = "full_almaty_fast";
}

function bindEvents() {
  els.run.addEventListener("click", runSimulation);
  els.quick.addEventListener("click", runQuickPreview);
  els.play.addEventListener("click", togglePlayback);
  els.reset.addEventListener("click", () => {
    state.frameIndex = 0;
    state.frameProgressMs = 0;
    renderFrame(0);
  });
  els.exportMetrics.addEventListener("click", () => exportRun("metrics"));
  els.exportRoads.addEventListener("click", () => exportRun("road-loads"));
}

async function runQuickPreview() {
  els.preset.value = "full_almaty_fast";
  els.vehicles.value = "180";
  els.steps.value = "500";
  els.speed.value = "1100";
  await runSimulation("/api/preview");
}

async function runSimulation(endpoint = "/api/simulations") {
  stopPlayback();
  setStatus("Running simulation...");
  state.selectedRoadId = state.selectedRoadId || null;
  els.selectedRoad.textContent = state.selectedRoadId || "auto";

  const payload = {
    preset_id: els.preset.value,
    vehicles: Number(els.vehicles.value),
    steps: Number(els.steps.value),
    seed: Number(els.seed.value),
    compare: els.compare.checked,
    scenario: {
      type: els.scenario.value,
      road_id: state.selectedRoadId,
      demand_surge: els.scenario.value === "demand_surge",
    },
  };

  try {
    const response = await fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || "Simulation failed");
    }
    const metadata = await response.json();
    state.currentRunId = metadata.id;
    const framesResponse = await fetch(`/api/simulations/${metadata.id}/frames`);
    const framePayload = await framesResponse.json();
    state.frames = framePayload.frames;
    state.baselineFrames = framePayload.baselineFrames || [];
    state.frameIndex = 0;
    state.frameProgressMs = 0;
    state.vehicleMarkers.clear();
    drawRoads(framePayload.roads, framePayload.scenarioRoads || []);
    renderRunMetadata(metadata);
    renderFrame(0);
    startPlayback();
    setStatus(`${endpoint.includes("preview") ? "Preview" : "Simulation"} ${metadata.id.slice(0, 8)} ready`);
  } catch (error) {
    setStatus(error.message);
  }
}

function drawRoads(roads, scenarioRoads) {
  state.roadsLayer.clearLayers();
  const scenarioSet = new Set(scenarioRoads);
  const bounds = [];

  for (const road of roads) {
    const color = roadColor(road.load, road.isOpen, scenarioSet.has(road.id));
    const line = L.polyline(road.coords, {
      color,
      weight: 2.5 + Math.min(road.load, 1.5) * 6,
      opacity: scenarioSet.has(road.id) ? 0.95 : 0.62,
    });
    line.trafficRoadId = road.id;
    line.on("click", () => {
      state.selectedRoadId = road.id;
      els.selectedRoad.textContent = road.id;
      highlightSelectedRoad();
    });
    line.bindTooltip(`${road.name}<br>load ${road.load.toFixed(2)}`);
    line.addTo(state.roadsLayer);
    bounds.push(...road.coords);
  }

  if (bounds.length > 0) {
    state.map.fitBounds(bounds, { padding: [22, 22] });
  }
}

function highlightSelectedRoad() {
  state.roadsLayer.eachLayer((layer) => {
    const points = layer.getLatLngs();
    layer.setStyle({ opacity: 0.62 });
    if (state.selectedRoadId && layer.trafficRoadId === state.selectedRoadId) {
      layer.setStyle({ opacity: 1, weight: 8 });
    }
    layer.setLatLngs(points);
  });
}

function renderRunMetadata(metadata) {
  const stats = metadata.stats;
  els.arrived.textContent = stats.arrived_vehicles;
  els.trip.textContent = `${(stats.average_trip_time_s / 60).toFixed(2)} min`;
  els.load.textContent = stats.max_road_load.toFixed(2);
  if (metadata.comparison) {
    els.delta.textContent = `${(metadata.comparison.delta.averageTripTimeS / 60).toFixed(2)} min`;
  } else {
    els.delta.textContent = "0.00 min";
  }
  els.hotRoads.innerHTML = "";
  for (const road of metadata.hotRoads || []) {
    const item = document.createElement("li");
    item.textContent = `${road.roadId} - ${road.load.toFixed(2)}`;
    els.hotRoads.appendChild(item);
  }
}

function renderFrame(progress = 0) {
  if (state.frames.length === 0) return;
  const frame = state.frames[state.frameIndex];
  const nextFrame = state.frames[Math.min(state.frameIndex + 1, state.frames.length - 1)];
  const nextById = new Map(nextFrame.vehicles.map((vehicle) => [vehicle.id, vehicle]));
  const activeIds = new Set();

  for (const vehicle of frame.vehicles) {
    activeIds.add(vehicle.id);
    const nextVehicle = nextById.get(vehicle.id) || vehicle;
    const lat = lerp(vehicle.lat, nextVehicle.lat, progress);
    const lng = lerp(vehicle.lng, nextVehicle.lng, progress);
    let marker = state.vehicleMarkers.get(vehicle.id);
    if (!marker) {
      marker = L.circleMarker([lat, lng], {
        radius: vehicle.state === "queued" ? 7 : 5,
        color: "#ffffff",
        weight: 2,
        fillColor: vehicle.state === "queued" ? "#d89024" : "#0f6fc6",
        fillOpacity: 0.95,
      }).addTo(state.vehicleLayer);
      state.vehicleMarkers.set(vehicle.id, marker);
    }
    marker.setLatLng([lat, lng]);
    marker.setStyle({
      radius: vehicle.state === "queued" ? 7 : 5,
      fillColor: vehicle.state === "queued" ? "#d89024" : "#0f6fc6",
    });
  }

  for (const [vehicleId, marker] of state.vehicleMarkers.entries()) {
    if (!activeIds.has(vehicleId)) {
      marker.remove();
      state.vehicleMarkers.delete(vehicleId);
    }
  }
  els.tick.textContent = frame.tick;
  els.moving.textContent = frame.vehicles.length;
}

function startPlayback() {
  stopPlayback();
  state.playing = true;
  els.play.textContent = "Pause";
  state.lastTimestamp = null;
  state.animationId = window.requestAnimationFrame(playbackLoop);
}

function stopPlayback() {
  if (state.animationId) {
    window.cancelAnimationFrame(state.animationId);
    state.animationId = null;
  }
}

function togglePlayback() {
  state.playing = !state.playing;
  els.play.textContent = state.playing ? "Pause" : "Start";
  if (state.playing && !state.animationId) {
    startPlayback();
  }
}

function playbackLoop(timestamp) {
  if (!state.playing || state.frames.length === 0) {
    state.animationId = null;
    return;
  }
  if (state.lastTimestamp === null) {
    state.lastTimestamp = timestamp;
  }
  const elapsed = timestamp - state.lastTimestamp;
  state.lastTimestamp = timestamp;
  const frameDuration = Number(els.speed.value);
  state.frameProgressMs += elapsed;
  while (state.frameProgressMs >= frameDuration) {
    state.frameProgressMs -= frameDuration;
    state.frameIndex = (state.frameIndex + 1) % state.frames.length;
  }
  renderFrame(state.frameProgressMs / frameDuration);
  state.animationId = window.requestAnimationFrame(playbackLoop);
}

async function exportRun(kind) {
  if (!state.currentRunId) return;
  const response = await fetch(`/api/simulations/${state.currentRunId}/export/${kind}`);
  const data = await response.json();
  setStatus(`Exported: ${data.path}`);
}

function roadColor(load, isOpen, scenario) {
  if (!isOpen) return "#222222";
  if (scenario) return "#0f6fc6";
  if (load >= 0.65) return "#cf3f32";
  if (load >= 0.25) return "#d89024";
  return "#586a75";
}

function setStatus(message) {
  els.status.textContent = message;
}

function lerp(start, end, progress) {
  return start + (end - start) * progress;
}
