const state = {
  config: {},
  providers: [],
  timePresets: [],
  zones: [],
  events: [],
  analytics: null,
  runStartMinute: 17 * 60,
  mapType: "leaflet",
  leafletMap: null,
  leafletRoadRenderer: null,
  leafletRoadsLayer: null,
  leafletVehicleLayer: null,
  leafletSignalLayer: null,
  leafletZoneLayer: null,
  mapglMap: null,
  mapglObjects: [],
  mapglVehicleMarkers: new Map(),
  vehicleCanvas: null,
  vehicleCanvasContext: null,
  lastRoads: [],
  lastScenarioRoads: [],
  signals: [],
  roadById: new Map(),
  frames: [],
  baselineFrames: [],
  procedural: false,
  proceduralVehicles: [],
  proceduralElapsedSeconds: 0,
  lastProceduralRenderSeconds: 0,
  targetDrawnVehicles: 25000,
  lastFpsTimestamp: 0,
  fpsFrames: 0,
  fps: 0,
  visibleVehicles: 0,
  drawnVehicles: 0,
  rerouteCount: 0,
  frameIndex: 0,
  animationId: null,
  lastTimestamp: null,
  frameProgressMs: 0,
  playing: true,
  selectedRoadId: null,
  currentRunId: null,
  vehicleMarkers: new Map(),
  activeRequest: null,
};

const els = {
  preset: document.getElementById("presetSelect"),
  tabs: Array.from(document.querySelectorAll(".tab-button")),
  panels: Array.from(document.querySelectorAll(".tab-panel")),
  mapMode: document.getElementById("mapModeSelect"),
  policy: document.getElementById("policySelect"),
  vehicles: document.getElementById("vehicleInput"),
  steps: document.getElementById("stepsInput"),
  seed: document.getElementById("seedInput"),
  speed: document.getElementById("speedInput"),
  timePreset: document.getElementById("timePresetSelect"),
  demandMode: document.getElementById("demandModeSelect"),
  reroute: document.getElementById("rerouteInput"),
  simTime: document.getElementById("timeInput"),
  timeSpeed: document.getElementById("timeSpeedInput"),
  vehicleSpeed: document.getElementById("vehicleSpeedInput"),
  speedColor: document.getElementById("speedColorSelect"),
  autoTime: document.getElementById("autoTimeInput"),
  heatmap: document.getElementById("heatmapInput"),
  showSignals: document.getElementById("showSignalsInput"),
  randomEvents: document.getElementById("randomEventsInput"),
  provider: document.getElementById("providerSelect"),
  scenario: document.getElementById("scenarioSelect"),
  capacity: document.getElementById("capacityInput"),
  speedFactor: document.getElementById("speedFactorInput"),
  signalDelay: document.getElementById("signalDelayInput"),
  duration: document.getElementById("durationInput"),
  compare: document.getElementById("compareInput"),
  refreshCache: document.getElementById("refreshCacheInput"),
  addEvent: document.getElementById("addEventButton"),
  eventPreset: document.getElementById("eventPresetButton"),
  timeline: document.getElementById("timelineList"),
  selectedRoad: document.getElementById("selectedRoad"),
  roadDetails: document.getElementById("roadDetails"),
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
  timeMetric: document.getElementById("timeMetric"),
  demand: document.getElementById("demandMetric"),
  fps: document.getElementById("fpsMetric"),
  drawn: document.getElementById("drawnMetric"),
  mode: document.getElementById("modeMetric"),
  roads: document.getElementById("roadsMetric"),
  avgSpeed: document.getElementById("avgSpeedMetric"),
  maxSpeed: document.getElementById("maxSpeedMetric"),
  providerState: document.getElementById("providerState"),
  exportState: document.getElementById("exportState"),
  hotRoads: document.getElementById("hotRoads"),
  corridorStats: document.getElementById("corridorStats"),
  odStats: document.getElementById("odStats"),
  coverageStats: document.getElementById("coverageStats"),
  congestionChart: document.getElementById("congestionChart"),
  speedChart: document.getElementById("speedChart"),
  exportMetrics: document.getElementById("exportMetrics"),
  exportRoads: document.getElementById("exportRoads"),
  exportReport: document.getElementById("exportReport"),
};

boot();

async function boot() {
  await loadConfig();
  await setMapMode(state.config.mapProvider === "2gis" ? "2gis" : "leaflet");
  await loadPresets();
  await loadTimePresets();
  await loadZones();
  await loadProviders();
  bindEvents();
  setStatus("Choose a preset, then press Run. Quick gives a smooth city-wide preview.");
}

async function loadConfig() {
  const response = await fetch("/api/config");
  state.config = await response.json();
  els.simTime.value = state.config.defaultTime || "17:00";
  els.policy.value = state.config.policy || "heuristic";
  els.provider.value = state.config.trafficDataProvider || "synthetic";
  if (!state.config.has2GisKey) {
    els.mapMode.querySelector("option[value='2gis']").textContent = "2GIS MapGL 3D (key required)";
  }
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

async function loadTimePresets() {
  const response = await fetch("/api/time-presets");
  const data = await response.json();
  state.timePresets = data.presets || [];
  els.timePreset.innerHTML = "";
  for (const preset of state.timePresets) {
    const option = document.createElement("option");
    option.value = preset.id;
    option.textContent = preset.name;
    option.dataset.time = preset.time || "";
    els.timePreset.appendChild(option);
  }
  els.timePreset.value = "evening_peak";
}

async function loadZones() {
  const response = await fetch("/api/zones");
  const data = await response.json();
  state.zones = data.zones || [];
}

async function loadProviders() {
  const response = await fetch("/api/traffic/providers");
  const data = await response.json();
  state.providers = data.providers || [];
  renderProviderState();
}

function bindEvents() {
  for (const button of els.tabs) {
    button.addEventListener("click", () => setActiveTab(button.dataset.tab));
  }
  els.mapMode.addEventListener("change", () => setMapMode(els.mapMode.value));
  els.provider.addEventListener("change", renderProviderState);
  els.showSignals.addEventListener("change", drawSignals);
  els.heatmap.addEventListener("change", () => renderFrame(0));
  els.demandMode.addEventListener("change", drawZones);
  els.timePreset.addEventListener("change", applyTimePreset);
  els.addEvent.addEventListener("click", addTimelineEvent);
  els.eventPreset.addEventListener("click", addTimelinePresets);
  els.run.addEventListener("click", runSmartSimulation);
  els.quick.addEventListener("click", runQuickPreview);
  els.play.addEventListener("click", togglePlayback);
  els.reset.addEventListener("click", () => {
    state.frameIndex = 0;
    state.frameProgressMs = 0;
    state.proceduralElapsedSeconds = 0;
    state.lastProceduralRenderSeconds = 0;
    renderFrame(0);
  });
  els.exportMetrics.addEventListener("click", () => exportRun("metrics"));
  els.exportRoads.addEventListener("click", () => exportRun("road-loads"));
  els.exportReport.addEventListener("click", () => exportRun("report"));
  renderTimeline();
}

function setActiveTab(tabName) {
  for (const button of els.tabs) {
    button.classList.toggle("active", button.dataset.tab === tabName);
  }
  for (const panel of els.panels) {
    panel.classList.toggle("active", panel.dataset.panel === tabName);
  }
}

function applyTimePreset() {
  const option = els.timePreset.selectedOptions[0];
  if (option && option.dataset.time) {
    els.simTime.value = option.dataset.time;
  }
}

async function setMapMode(mode) {
  stopPlayback();
  clearMapObjects();
  if (mode === "2gis") {
    if (!state.config.has2GisKey || !state.config.twoGisApiKey) {
      els.mapMode.value = "leaflet";
      setStatus("2GIS MapGL needs 2GIS_API_KEY. Leaflet fallback is active.");
      mode = "leaflet";
    } else {
      await init2GisMap();
    }
  }
  if (mode === "leaflet") {
    initLeafletMap();
  }
  state.mapType = mode;
  els.mapMode.value = mode;
  document.body.classList.toggle("map-mode-3d", mode === "2gis");
  if (state.lastRoads.length) {
    drawRoads(state.lastRoads, state.lastScenarioRoads);
    renderFrame(0);
  }
}

function initLeafletMap() {
  destroyMapglMap();
  if (state.leafletMap) return;
  const container = document.getElementById("map");
  container.innerHTML = "";
  state.leafletMap = L.map("map", { zoomControl: false }).setView([43.238, 76.945], 12);
  state.leafletRoadRenderer = L.canvas({ padding: 0.5 });
  L.control.zoom({ position: "bottomright" }).addTo(state.leafletMap);
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: "&copy; OpenStreetMap contributors",
  }).addTo(state.leafletMap);
  state.leafletRoadsLayer = L.layerGroup().addTo(state.leafletMap);
  state.leafletVehicleLayer = L.layerGroup().addTo(state.leafletMap);
  state.leafletSignalLayer = L.layerGroup().addTo(state.leafletMap);
  state.leafletZoneLayer = L.layerGroup().addTo(state.leafletMap);
  ensureVehicleCanvas();
  state.leafletMap.on("resize move zoomend", resizeVehicleCanvas);
  drawZones();
}

async function init2GisMap() {
  destroyLeafletMap();
  await loadMapglScript();
  const container = document.getElementById("map");
  container.innerHTML = "";
  state.mapglMap = new mapgl.Map("map", {
    center: [76.945, 43.238],
    zoom: 12,
    pitch: 45,
    rotation: 12,
    key: state.config.twoGisApiKey,
  });
}

function loadMapglScript() {
  if (window.mapgl) return Promise.resolve();
  return new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.src = "https://mapgl.2gis.com/api/js/v1";
    script.onload = resolve;
    script.onerror = () => reject(new Error("Could not load 2GIS MapGL script"));
    document.head.appendChild(script);
  });
}

function destroyLeafletMap() {
  if (!state.leafletMap) return;
  state.leafletMap.remove();
  state.leafletMap = null;
  state.leafletRoadRenderer = null;
  state.leafletRoadsLayer = null;
  state.leafletVehicleLayer = null;
  state.leafletSignalLayer = null;
  state.leafletZoneLayer = null;
  state.vehicleCanvas = null;
  state.vehicleCanvasContext = null;
  state.vehicleMarkers.clear();
}

function destroyMapglMap() {
  if (!state.mapglMap) return;
  clearMapObjects();
  state.mapglMap.destroy();
  state.mapglMap = null;
  state.mapglVehicleMarkers.clear();
}

async function runSmartSimulation() {
  const isFullCity = els.preset.value === "full_almaty" || els.preset.value === "full_almaty_fast";
  const massMode = Number(els.vehicles.value) > 3000;
  const endpoint = (isFullCity && !els.compare.checked) || massMode ? "/api/preview" : "/api/simulations";
  await runSimulation(endpoint);
}

async function runQuickPreview() {
  els.preset.value = "full_almaty_fast";
  els.vehicles.value = "8000";
  els.steps.value = "500";
  els.speed.value = "700";
  els.vehicleSpeed.value = "2";
  els.demandMode.value = "od_zones";
  els.heatmap.checked = true;
  await runSimulation("/api/preview");
}

async function runSimulation(endpoint = "/api/simulations") {
  stopPlayback();
  if (state.activeRequest) {
    state.activeRequest.abort();
  }
  state.activeRequest = new AbortController();
  setStatus(endpoint.includes("preview") ? "Running fast city-wide preview..." : "Running research simulation...");
  els.selectedRoad.textContent = state.selectedRoadId || "auto";
  els.run.disabled = true;
  els.quick.disabled = true;

  const payload = {
    preset_id: els.preset.value,
    vehicles: Number(els.vehicles.value),
    steps: Number(els.steps.value),
    seed: Number(els.seed.value),
    refresh_cache: els.refreshCache.checked,
    compare: els.compare.checked,
    manual_time: els.simTime.value || "17:00",
    time_preset: els.timePreset.value || "manual",
    auto_time: els.autoTime.checked,
    time_speed_multiplier: Number(els.timeSpeed.value),
    policy: els.policy.value,
    demand_mode: els.demandMode.value,
    reroute_interval_ticks: Number(els.reroute.value),
    random_events: els.randomEvents.checked,
    events: state.events.map((event) => ({
      id: event.id,
      type: event.type,
      road_id: event.roadId,
      start_time: event.startTime,
      duration_minutes: event.durationMinutes,
      enabled: event.enabled,
      capacity_factor: event.capacityFactor,
      speed_factor: event.speedFactor,
      signal_delay_s: event.signalDelayS,
    })),
    scenario: {
      type: els.scenario.value,
      road_id: state.selectedRoadId,
      capacity_factor: Number(els.capacity.value),
      speed_factor: Number(els.speedFactor.value),
      signal_delay_s: Number(els.signalDelay.value),
      duration_minutes: Number(els.duration.value),
      start_time: els.simTime.value || "17:00",
      demand_surge: els.scenario.value === "demand_surge",
    },
  };

  try {
    const response = await fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      signal: state.activeRequest.signal,
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
    state.events = mergeReturnedEvents(framePayload.events || metadata.events || []);
    renderTimeline();
    state.procedural = Boolean(framePayload.procedural);
    state.proceduralVehicles = framePayload.proceduralVehicles || [];
    state.rerouteCount = 0;
    state.proceduralElapsedSeconds = 0;
    state.lastProceduralRenderSeconds = 0;
    state.baselineFrames = framePayload.baselineFrames || [];
    state.frameIndex = 0;
    state.frameProgressMs = 0;
    state.vehicleMarkers.clear();
    state.mapglVehicleMarkers.clear();
    drawRoads(framePayload.roads, framePayload.scenarioRoads || []);
    await loadSignals();
    renderRunMetadata(metadata);
    await loadAnalytics(metadata.id);
    renderFrame(0);
    startPlayback();
    setStatus(`${endpoint.includes("preview") ? "Preview" : "Simulation"} ${metadata.id.slice(0, 8)} ready`);
  } catch (error) {
    if (error.name !== "AbortError") {
      setStatus(error.message);
    }
  } finally {
    els.run.disabled = false;
    els.quick.disabled = false;
    state.activeRequest = null;
  }
}

function drawRoads(roads, scenarioRoads) {
  state.lastRoads = roads;
  state.lastScenarioRoads = scenarioRoads;
  state.roadById = new Map(roads.map((road) => [road.id, road]));
  if (state.mapType === "2gis" && state.mapglMap) {
    drawMapglRoads(roads, scenarioRoads);
  } else {
    drawLeafletRoads(roads, scenarioRoads);
  }
  drawSignals();
  drawZones();
}

async function loadSignals() {
  try {
    const response = await fetch(`/api/signals?preset_id=${encodeURIComponent(els.preset.value)}`);
    if (!response.ok) throw new Error("signals unavailable");
    const payload = await response.json();
    state.signals = payload.signals || [];
    drawSignals();
  } catch {
    state.signals = [];
    drawSignals();
  }
}

function drawLeafletRoads(roads, scenarioRoads) {
  state.leafletRoadsLayer.clearLayers();
  state.leafletVehicleLayer.clearLayers();
  clearVehicleCanvas();
  const scenarioSet = new Set(scenarioRoads);
  const bounds = [];

  for (const road of roads) {
    const color = roadColor(road.load, road.isOpen, scenarioSet.has(road.id));
    const line = L.polyline(road.coords, {
      color,
      weight: 2.5 + Math.min(road.load, 1.5) * 6,
      opacity: scenarioSet.has(road.id) ? 0.95 : 0.62,
      renderer: state.leafletRoadRenderer,
    });
    line.trafficRoadId = road.id;
    line.on("click", () => selectRoad(road.id));
    line.bindTooltip(`${road.name}<br>load ${road.load.toFixed(2)}`);
    line.addTo(state.leafletRoadsLayer);
    bounds.push(...road.coords);
  }

  if (bounds.length > 0) {
    state.leafletMap.fitBounds(bounds, { padding: [22, 22] });
  }
  highlightSelectedRoad();
}

function drawMapglRoads(roads, scenarioRoads) {
  clearMapObjects();
  const scenarioSet = new Set(scenarioRoads);
  let lngTotal = 0;
  let latTotal = 0;
  let pointCount = 0;
  for (const road of roads) {
    const line = new mapgl.Polyline(state.mapglMap, {
      coordinates: road.coords.map((point) => [point[1], point[0]]),
      width: 2 + Math.min(road.load, 1.5) * 7,
      color: roadColor(road.load, road.isOpen, scenarioSet.has(road.id)),
      zIndex: scenarioSet.has(road.id) ? 3 : 1,
    });
    line.on("click", () => selectRoad(road.id));
    state.mapglObjects.push(line);
    for (const point of road.coords) {
      latTotal += point[0];
      lngTotal += point[1];
      pointCount += 1;
    }
  }
  if (pointCount > 0) {
    state.mapglMap.setCenter([lngTotal / pointCount, latTotal / pointCount]);
    state.mapglMap.setZoom(12);
  }
}

function clearMapObjects() {
  for (const object of state.mapglObjects) {
    object.destroy();
  }
  state.mapglObjects = [];
  for (const marker of state.mapglVehicleMarkers.values()) {
    marker.destroy();
  }
  state.mapglVehicleMarkers.clear();
}

function drawSignals() {
  if (!state.leafletSignalLayer) return;
  state.leafletSignalLayer.clearLayers();
  if (!els.showSignals.checked) return;
  for (const signal of state.signals) {
    L.circleMarker([signal.lat, signal.lng], {
      radius: 5,
      color: "#ffffff",
      weight: 1.5,
      fillColor: "#cf3f32",
      fillOpacity: 0.9,
      pane: "markerPane",
    })
      .bindTooltip(`Traffic signal<br>delay ${Number(signal.delayS || 0).toFixed(0)}s`)
      .addTo(state.leafletSignalLayer);
  }
}

function drawZones() {
  if (!state.leafletZoneLayer) return;
  state.leafletZoneLayer.clearLayers();
  if (els.demandMode.value !== "od_zones") return;
  for (const zone of state.zones) {
    L.circle([zone.lat, zone.lng], {
      radius: Number(zone.radiusM || 1800),
      color: zone.kind === "residential" ? "#0f6fc6" : zone.kind === "transport" ? "#d89024" : "#0f766e",
      weight: 1.5,
      opacity: 0.72,
      fillColor: zone.kind === "residential" ? "#0f6fc6" : zone.kind === "transport" ? "#d89024" : "#0f766e",
      fillOpacity: 0.08,
      interactive: false,
    }).addTo(state.leafletZoneLayer);
  }
}

async function selectRoad(roadId) {
  state.selectedRoadId = roadId;
  els.selectedRoad.textContent = roadId;
  highlightSelectedRoad();
  await loadRoadDetails(roadId);
}

async function loadRoadDetails(roadId) {
  try {
    const response = await fetch(`/api/roads/${encodeURIComponent(roadId)}?preset_id=${encodeURIComponent(els.preset.value)}`);
    if (!response.ok) throw new Error("road lookup failed");
    const payload = await response.json();
    const road = payload.road;
    const liveRoad = state.roadById.get(roadId);
    const liveLoad = liveRoad ? ` | live load ${Number(liveRoad.load || 0).toFixed(2)}` : "";
    const eventCount = liveRoad && Array.isArray(liveRoad.timelineEvents) ? liveRoad.timelineEvents.length : 0;
    const eventText = eventCount ? ` | timeline events ${eventCount}` : "";
    els.roadDetails.textContent = `${road.name} | ${road.roadClass} | ${road.lanes} lanes (${road.lanesSource}) | cap ${road.effectiveCapacity} | limit ${road.maxSpeedKph.toFixed(0)} kph (${road.speedSource}) | est ${road.estimatedSpeedKph.toFixed(0)} kph | signals ${road.signalCount}${liveLoad}${eventText}`;
    const statsResponse = await fetch(`/api/statistics/road/${encodeURIComponent(roadId)}?provider_id=${encodeURIComponent(els.provider.value)}`);
    const stats = await statsResponse.json();
    if (stats.observations.length) {
      const peak = stats.observations.reduce((best, item) => (item.load > best.load ? item : best), stats.observations[0]);
      els.roadDetails.textContent += ` | provider peak ${peak.time} load ${peak.load.toFixed(2)}`;
    }
  } catch {
    els.roadDetails.textContent = "Road details are unavailable for this road.";
  }
}

function highlightSelectedRoad() {
  if (!state.leafletRoadsLayer) return;
  state.leafletRoadsLayer.eachLayer((layer) => {
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
  state.runStartMinute = parseTimeToMinute(stats.time || els.simTime.value || "17:00");
  els.arrived.textContent = stats.arrived_vehicles;
  els.trip.textContent = `${(stats.average_trip_time_s / 60).toFixed(2)} min`;
  els.load.textContent = stats.max_road_load.toFixed(2);
  els.timeMetric.textContent = stats.time || els.simTime.value || "17:00";
  els.demand.textContent = `${Number(stats.demand_multiplier || 1).toFixed(2)}x`;
  els.mode.textContent = metadata.procedural ? "mass preview" : "research";
  els.roads.textContent = metadata.roadCount;
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

async function loadAnalytics(runId) {
  try {
    const response = await fetch(`/api/simulations/${runId}/analytics`);
    if (!response.ok) throw new Error("analytics unavailable");
    const payload = await response.json();
    state.analytics = payload.analytics;
    renderAnalytics();
  } catch {
    state.analytics = null;
    renderAnalytics();
  }
}

function renderAnalytics() {
  const analytics = state.analytics || {};
  drawMiniChart(els.congestionChart, analytics.congestionOverTime || [], "#cf3f32");
  drawMiniChart(els.speedChart, analytics.averageSpeedOverTime || [], "#0f766e");
  els.corridorStats.innerHTML = "";
  for (const corridor of analytics.corridorStats || []) {
    const row = document.createElement("div");
    row.className = "mini-row";
    row.innerHTML = `<strong>${escapeHtml(corridor.name || corridor.id)}</strong><span>${corridor.roadCount} roads | load ${Number(corridor.averageLoad || 0).toFixed(2)} | speed ${Number(corridor.estimatedSpeedKph || 0).toFixed(0)} kph</span>`;
    els.corridorStats.appendChild(row);
  }
  els.odStats.innerHTML = "";
  for (const pair of analytics.odPairs || []) {
    const row = document.createElement("div");
    row.className = "mini-row";
    row.innerHTML = `<strong>${escapeHtml(pair.origin)} -> ${escapeHtml(pair.destination)}</strong><span>${Number(pair.vehicles || 0)} vehicles</span>`;
    els.odStats.appendChild(row);
  }
  const coverage = analytics.routeCoverage || {};
  els.coverageStats.innerHTML = "";
  const coverageRow = document.createElement("div");
  coverageRow.className = "mini-row";
  coverageRow.innerHTML = `<strong>${Math.round(Number(coverage.coverageRatio || 0) * 100)}% road coverage</strong><span>${Number(coverage.coveredRoads || 0)} / ${Number(coverage.totalRoads || 0)} roads | avg route ${Number(coverage.averageRouteRoads || 0).toFixed(1)} roads</span>`;
  els.coverageStats.appendChild(coverageRow);
}

function drawMiniChart(canvas, series, color) {
  const ctx = canvas.getContext("2d");
  const width = canvas.width;
  const height = canvas.height;
  ctx.clearRect(0, 0, width, height);
  ctx.fillStyle = "#fffdf8";
  ctx.fillRect(0, 0, width, height);
  ctx.strokeStyle = "#d8d1c2";
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(0, height - 16);
  ctx.lineTo(width, height - 16);
  ctx.stroke();
  if (!series.length) return;
  const values = series.map((item) => Number(item.value || 0));
  const max = Math.max(...values, 1);
  ctx.strokeStyle = color;
  ctx.lineWidth = 2.5;
  ctx.beginPath();
  series.forEach((item, index) => {
    const x = series.length === 1 ? 0 : (index / (series.length - 1)) * width;
    const y = height - 18 - (Number(item.value || 0) / max) * (height - 28);
    if (index === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.stroke();
}

function addTimelineEvent() {
  state.events.push({
    id: `ui-${Date.now()}`,
    type: els.scenario.value === "none" ? "accident" : els.scenario.value,
    roadId: state.selectedRoadId,
    startTime: els.simTime.value || "17:10",
    durationMinutes: Number(els.duration.value || 40),
    enabled: true,
    capacityFactor: Number(els.capacity.value || 0.35),
    speedFactor: Number(els.speedFactor.value || 0.45),
    signalDelayS: Number(els.signalDelay.value || 60),
  });
  renderTimeline();
}

function addTimelinePresets() {
  const roadId = state.selectedRoadId;
  state.events.push(
    { id: `preset-accident-${Date.now()}`, type: "accident", roadId, startTime: "17:10", durationMinutes: 35, enabled: true, capacityFactor: 0.35, speedFactor: 0.4, signalDelayS: 60 },
    { id: `preset-repair-${Date.now()}`, type: "repair", roadId, startTime: "17:40", durationMinutes: 40, enabled: true, capacityFactor: 0.1, speedFactor: 0.2, signalDelayS: 60 },
    { id: `preset-weather-${Date.now()}`, type: "weather", roadId: null, startTime: "18:00", durationMinutes: 45, enabled: true, capacityFactor: 0.75, speedFactor: 0.72, signalDelayS: 60 },
  );
  renderTimeline();
}

function renderTimeline() {
  els.timeline.innerHTML = "";
  if (!state.events.length) {
    const empty = document.createElement("div");
    empty.className = "timeline-event";
    empty.textContent = "No timeline events yet.";
    els.timeline.appendChild(empty);
    return;
  }
  const currentMinute = currentSimulationMinute();
  state.events.forEach((event, index) => {
    const active = isEventActive(event, currentMinute);
    const item = document.createElement("div");
    item.className = `timeline-event${active ? " active" : ""}`;
    item.innerHTML = `
      <strong>${escapeHtml(event.type)} | ${escapeHtml(event.startTime)}-${escapeHtml(eventEndTime(event))}</strong>
      <span>${active ? "active now" : "scheduled"} | ${escapeHtml(event.roadId || "all roads")} | ${event.durationMinutes} min | speed x${Number(event.speedFactor || 1).toFixed(2)}</span>
      <div class="timeline-actions">
        <button type="button" data-action="toggle">${event.enabled === false ? "Enable" : "Disable"}</button>
        <button type="button" data-action="remove">Remove</button>
      </div>`;
    item.querySelector('[data-action="toggle"]').addEventListener("click", () => {
      event.enabled = event.enabled === false;
      renderTimeline();
    });
    item.querySelector('[data-action="remove"]').addEventListener("click", () => {
      state.events.splice(index, 1);
      renderTimeline();
    });
    els.timeline.appendChild(item);
  });
}

function mergeReturnedEvents(events) {
  return events.map((event, index) => ({
    id: event.id || `server-${index}`,
    type: event.type || "accident",
    roadId: event.roadId || event.road_id || null,
    startTime: event.startTime || event.start_time || "17:10",
    durationMinutes: Number(event.durationMinutes || event.duration_minutes || 40),
    enabled: event.enabled !== false,
    capacityFactor: Number(event.capacityFactor || event.capacity_factor || 0.35),
    speedFactor: Number(event.speedFactor || event.speed_factor || 0.45),
    signalDelayS: Number(event.signalDelayS || event.signal_delay_s || 60),
  }));
}

function renderFrame(progress = 0) {
  if (state.procedural) {
    renderProceduralVehicles();
    els.tick.textContent = Math.floor(state.proceduralElapsedSeconds / 10);
    els.moving.textContent = state.proceduralVehicles.length;
    return;
  }
  if (state.frames.length === 0) return;
  const frame = state.frames[state.frameIndex];
  const nextFrame = state.frames[Math.min(state.frameIndex + 1, state.frames.length - 1)];
  const nextById = new Map(nextFrame.vehicles.map((vehicle) => [vehicle.id, vehicle]));
  if (state.mapType === "2gis" && state.mapglMap) {
    renderMapglVehicles(frame, nextById, progress);
  } else {
    renderLeafletVehicles(frame, nextById, progress);
  }
  els.tick.textContent = frame.tick;
  els.moving.textContent = frame.vehicles.length;
}

function renderLeafletVehicles(frame, nextById, progress) {
  const points = [];
  for (const vehicle of frame.vehicles) {
    const nextVehicle = nextById.get(vehicle.id) || vehicle;
    points.push({
      lat: lerp(vehicle.lat, nextVehicle.lat, progress),
      lng: lerp(vehicle.lng, nextVehicle.lng, progress),
      state: vehicle.state,
      speedKph: vehicle.speedKph || 0,
    });
  }
  drawVehiclePoints(points);
}

function createLeafletDotMarker(lat, lng, stateName) {
  return L.circleMarker([lat, lng], {
    radius: stateName === "queued" ? 7 : 5,
    color: "#ffffff",
    weight: 2,
    fillColor: stateName === "queued" ? "#d89024" : "#0f6fc6",
    fillOpacity: 0.95,
  }).addTo(state.leafletVehicleLayer);
}

function createLeafletCarMarker(lat, lng) {
  return L.marker([lat, lng], {
    icon: L.divIcon({
      className: "vehicle-car",
      iconSize: [17, 10],
      iconAnchor: [8, 5],
    }),
  }).addTo(state.leafletVehicleLayer);
}

function renderProceduralVehicles() {
  if (!state.leafletMap) return;
  ensureVehicleCanvas();
  const ctx = state.vehicleCanvasContext;
  if (!ctx) return;
  clearVehicleCanvas();
  const deltaSeconds = Math.max(0, state.proceduralElapsedSeconds - state.lastProceduralRenderSeconds);
  state.lastProceduralRenderSeconds = state.proceduralElapsedSeconds;
  const zoom = state.leafletMap.getZoom();
  const radius = zoom >= 15 ? 4.2 : zoom >= 13 ? 3.2 : 2.1;
  const border = zoom >= 14 && state.proceduralVehicles.length < 30000;
  const maxDraw = drawBudgetForFps();
  const visibleStride = Math.max(1, Math.ceil(state.proceduralVehicles.length / maxDraw));
  const heatStride = els.heatmap.checked ? Math.max(1, Math.ceil(state.proceduralVehicles.length / 4500)) : Infinity;
  let visible = 0;
  let drawn = 0;
  let heatIndex = 0;
  ctx.globalAlpha = 0.92;
  for (const vehicle of state.proceduralVehicles) {
    const road = state.roadById.get(vehicle.roadId || vehicle.currentRoadId);
    if (!road || !road.isOpen || road.coords.length < 2) continue;
    const currentFlowFactor = roadFlowFactor(road);
    vehicle.offset += vehicle.speed * deltaSeconds * currentFlowFactor * Number(els.vehicleSpeed.value || 1);
    vehicle.currentSpeedKph = Math.max(0, Number(vehicle.speedKph || road.maxSpeedKph || 30) * currentFlowFactor * Number(els.vehicleSpeed.value || 1));
    let activeRoad = road;
    let guard = 0;
    while (vehicle.offset >= 1 && guard < 8) {
      vehicle.offset -= 1;
      vehicle.roadId = advanceVehicleToNextRoad(activeRoad, vehicle) || vehicle.roadId;
      activeRoad = state.roadById.get(vehicle.roadId) || activeRoad;
      guard += 1;
    }
    const point = interpolateRoad(activeRoad.coords, vehicle.offset);
    const pixel = state.leafletMap.latLngToContainerPoint(point);
    if (pixel.x < -8 || pixel.y < -8 || pixel.x > state.vehicleCanvas.clientWidth + 8 || pixel.y > state.vehicleCanvas.clientHeight + 8) {
      continue;
    }
    visible += 1;
    if (visibleStride > 1 && visible % visibleStride !== 0) {
      continue;
    }
    if (drawn >= maxDraw) {
      continue;
    }
    heatIndex += 1;
    if (els.heatmap.checked && heatIndex % heatStride === 0) {
      drawHeatPoint(ctx, pixel.x, pixel.y, Math.min(1, Number(activeRoad.load || 0.2) + 0.15));
    }
    drawVehicleCircle(ctx, pixel.x, pixel.y, vehicle.state || "moving", radius, border, vehicle.currentSpeedKph || 0);
    drawn += 1;
  }
  ctx.globalAlpha = 1;
  state.visibleVehicles = visible;
  state.drawnVehicles = drawn;
  updateSpeedMetrics();
  updatePerformanceMetrics();
  if (Math.floor(state.proceduralElapsedSeconds) % 5 === 0) {
    renderTimeline();
  }
}

function ensureVehicleCanvas() {
  if (!state.leafletMap || state.vehicleCanvas) return;
  const canvas = document.createElement("canvas");
  canvas.className = "vehicle-canvas";
  state.leafletMap.getContainer().appendChild(canvas);
  state.vehicleCanvas = canvas;
  state.vehicleCanvasContext = canvas.getContext("2d");
  resizeVehicleCanvas();
}

function resizeVehicleCanvas() {
  if (!state.vehicleCanvas || !state.leafletMap) return;
  const container = state.leafletMap.getContainer();
  const ratio = window.devicePixelRatio || 1;
  const width = container.clientWidth;
  const height = container.clientHeight;
  state.vehicleCanvas.style.width = `${width}px`;
  state.vehicleCanvas.style.height = `${height}px`;
  state.vehicleCanvas.width = Math.max(1, Math.floor(width * ratio));
  state.vehicleCanvas.height = Math.max(1, Math.floor(height * ratio));
  state.vehicleCanvasContext.setTransform(ratio, 0, 0, ratio, 0, 0);
}

function clearVehicleCanvas() {
  if (!state.vehicleCanvasContext || !state.vehicleCanvas) return;
  const ratio = window.devicePixelRatio || 1;
  state.vehicleCanvasContext.clearRect(0, 0, state.vehicleCanvas.width / ratio, state.vehicleCanvas.height / ratio);
}

function drawVehiclePoints(points) {
  ensureVehicleCanvas();
  const ctx = state.vehicleCanvasContext;
  if (!ctx || !state.leafletMap) return;
  clearVehicleCanvas();
  const zoom = state.leafletMap.getZoom();
  const radius = zoom >= 15 ? 4.2 : zoom >= 13 ? 3.2 : 2.2;
  const border = zoom >= 14 && points.length < 30000;
  ctx.globalAlpha = 0.92;
  let visible = 0;
  let drawn = 0;
  for (const point of points) {
    const pixel = state.leafletMap.latLngToContainerPoint([point.lat, point.lng]);
    if (pixel.x < -8 || pixel.y < -8 || pixel.x > state.vehicleCanvas.clientWidth + 8 || pixel.y > state.vehicleCanvas.clientHeight + 8) {
      continue;
    }
    visible += 1;
    if (els.heatmap.checked) {
      drawHeatPoint(ctx, pixel.x, pixel.y, 0.35);
    }
    drawVehicleCircle(ctx, pixel.x, pixel.y, point.state, radius, border, point.speedKph || 0);
    drawn += 1;
  }
  ctx.globalAlpha = 1;
  state.visibleVehicles = visible;
  state.drawnVehicles = drawn;
  updatePerformanceMetrics();
}

function drawVehicleCircle(ctx, x, y, stateName, radius, border, speedKph = 0) {
  ctx.beginPath();
  ctx.arc(x, y, stateName === "queued" ? radius + 1.2 : radius, 0, Math.PI * 2);
  ctx.fillStyle = vehicleColor(stateName, speedKph);
  ctx.fill();
  if (border) {
    ctx.lineWidth = 1.2;
    ctx.strokeStyle = "#ffffff";
    ctx.stroke();
  }
}

function drawHeatPoint(ctx, x, y, weight) {
  const gradient = ctx.createRadialGradient(x, y, 0, x, y, 28);
  const alpha = Math.max(0.05, Math.min(weight, 1)) * 0.24;
  gradient.addColorStop(0, `rgba(207, 63, 50, ${alpha})`);
  gradient.addColorStop(0.55, `rgba(216, 144, 36, ${alpha * 0.55})`);
  gradient.addColorStop(1, "rgba(207, 63, 50, 0)");
  ctx.fillStyle = gradient;
  ctx.fillRect(x - 28, y - 28, 56, 56);
}

function interpolateRoad(coords, ratio) {
  if (coords.length === 2) {
    return [lerp(coords[0][0], coords[1][0], ratio), lerp(coords[0][1], coords[1][1], ratio)];
  }
  const lengths = [];
  let total = 0;
  for (let index = 0; index < coords.length - 1; index += 1) {
    const length = distance(coords[index], coords[index + 1]);
    lengths.push(length);
    total += length;
  }
  if (total <= 0) return coords[0];
  let target = total * ratio;
  for (let index = 0; index < lengths.length; index += 1) {
    if (target <= lengths[index]) {
      const local = lengths[index] > 0 ? target / lengths[index] : 0;
      return [lerp(coords[index][0], coords[index + 1][0], local), lerp(coords[index][1], coords[index + 1][1], local)];
    }
    target -= lengths[index];
  }
  return coords[coords.length - 1];
}

function renderMapglVehicles(frame, nextById, progress) {
  const activeIds = new Set();
  const icon = carIconDataUrl("#0f6fc6");
  const queuedIcon = carIconDataUrl("#d89024");
  for (const vehicle of frame.vehicles) {
    activeIds.add(vehicle.id);
    const nextVehicle = nextById.get(vehicle.id) || vehicle;
    const lat = lerp(vehicle.lat, nextVehicle.lat, progress);
    const lng = lerp(vehicle.lng, nextVehicle.lng, progress);
    let marker = state.mapglVehicleMarkers.get(vehicle.id);
    if (!marker) {
      marker = new mapgl.Marker(state.mapglMap, {
        coordinates: [lng, lat],
        icon: vehicle.state === "queued" ? queuedIcon : icon,
        size: [22, 14],
        anchor: [11, 7],
        zIndex: 5,
      });
      state.mapglVehicleMarkers.set(vehicle.id, marker);
    }
    marker.setCoordinates([lng, lat]);
  }
  for (const [vehicleId, marker] of state.mapglVehicleMarkers.entries()) {
    if (!activeIds.has(vehicleId)) {
      marker.destroy();
      state.mapglVehicleMarkers.delete(vehicleId);
    }
  }
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
  if (state.procedural) {
    state.proceduralElapsedSeconds += (elapsed / Math.max(frameDuration, 1)) * 10;
  } else {
    state.frameProgressMs += elapsed;
    while (state.frameProgressMs >= frameDuration) {
      state.frameProgressMs -= frameDuration;
      state.frameIndex = (state.frameIndex + 1) % state.frames.length;
    }
  }
  renderFrame(state.frameProgressMs / frameDuration);
  trackFps(timestamp);
  state.animationId = window.requestAnimationFrame(playbackLoop);
}

async function exportRun(kind) {
  if (!state.currentRunId) return;
  const response = await fetch(`/api/simulations/${state.currentRunId}/export/${kind}`);
  const data = await response.json();
  if (!response.ok) {
    setStatus(data.detail || "Export failed");
    return;
  }
  setStatus(`Exported: ${data.path}`);
  if (els.exportState) {
    els.exportState.textContent = `Exported: ${data.path}`;
  }
}

function renderProviderState() {
  const provider = state.providers.find((item) => item.id === els.provider.value);
  if (!provider) {
    els.providerState.textContent = `Traffic provider: ${els.provider.value}`;
    return;
  }
  const availability = provider.available ? "ready" : "needs key/data";
  const mode = provider.mode || provider.path || "local";
  els.providerState.textContent = `Traffic provider: ${provider.id} | ${availability} | ${mode}`;
}

function roadColor(load, isOpen, scenario) {
  if (!isOpen) return "#222222";
  if (scenario) return "#0f6fc6";
  if (load >= 0.65) return "#cf3f32";
  if (load >= 0.25) return "#d89024";
  return "#586a75";
}

function roadFlowFactor(road) {
  const incidentFactor = Number(road.speedModifier || 1);
  const load = Number(road.load || 0);
  const signalDelay = Number(road.signalDelayS || 0);
  const eventFactor = activeRoadEventFactor(road);
  const congestionFactor = Math.max(0.18, 1 - Math.min(load, 1.25) * 0.62);
  const signalFactor = Math.max(0.55, 1 - Math.min(signalDelay, 45) / 120);
  return incidentFactor * congestionFactor * signalFactor * eventFactor;
}

function advanceVehicleToNextRoad(road, vehicle) {
  const route = Array.isArray(vehicle.routeRoadIds) ? vehicle.routeRoadIds : [];
  if (route.length > 1) {
    const nextRouteIndex = Number(vehicle.routeIndex || 0) + 1;
    const plannedId = route[nextRouteIndex];
    const plannedRoad = state.roadById.get(plannedId);
    if (plannedRoad && plannedRoad.isOpen && roadFlowFactor(plannedRoad) > 0.12) {
      vehicle.routeIndex = nextRouteIndex;
      return plannedId;
    }
    const alternative = chooseNextRoad(road, vehicle);
    if (alternative && alternative !== plannedId) {
      vehicle.routeIndex = nextRouteIndex;
      vehicle.reroutes = Number(vehicle.reroutes || 0) + 1;
      state.rerouteCount += 1;
      return alternative;
    }
    if (nextRouteIndex >= route.length) {
      vehicle.routeIndex = 0;
      return route[0];
    }
  }
  return chooseNextRoad(road, vehicle);
}

function chooseNextRoad(road, vehicle) {
  const candidates = Array.isArray(road.nextRoadCandidates) && road.nextRoadCandidates.length ? road.nextRoadCandidates : [road.nextRoadId];
  let bestId = candidates[0] || road.nextRoadId;
  let bestScore = -Infinity;
  for (const roadId of candidates) {
    const candidate = state.roadById.get(roadId);
    if (!candidate || !candidate.isOpen) continue;
    const load = Number(candidate.load || 0);
    const factor = roadFlowFactor(candidate);
    const routeBonus = Array.isArray(vehicle.routeRoadIds) && vehicle.routeRoadIds.includes(roadId) ? 0.08 : 0;
    const behaviorBonus = vehicle.destinationZone ? 0.03 : 0;
    const score = factor - load * 0.35 + behaviorBonus + routeBonus + deterministicJitter(`${vehicle.roadId}:${roadId}`);
    if (score > bestScore) {
      bestScore = score;
      bestId = roadId;
    }
  }
  return bestId;
}

function activeRoadEventFactor(road) {
  const events = Array.isArray(road.timelineEvents) ? road.timelineEvents : [];
  const minute = currentSimulationMinute();
  let factor = 1;
  for (const event of events) {
    if (!isEventActive(event, minute)) continue;
    if (event.type === "repair" || event.type === "closure") return 0.05;
    if (event.type === "weather" || event.type === "accident" || event.type === "capacity_reduction") {
      factor *= Number(event.speedFactor || event.speed_factor || 0.5);
    }
    if (event.type === "signal") {
      factor *= Math.max(0.35, 1 - Number(event.signalDelayS || event.signal_delay_s || 60) / 180);
    }
  }
  return Math.max(0.05, factor);
}

function vehicleColor(stateName, speedKph) {
  if (stateName === "queued") return "#d89024";
  if (els.speedColor.value === "off") return "#0f6fc6";
  if (speedKph >= 55) return "#0f766e";
  if (speedKph >= 32) return "#0f6fc6";
  if (speedKph >= 14) return "#d89024";
  return "#cf3f32";
}

function setStatus(message) {
  els.status.textContent = message;
}

function lerp(start, end, progress) {
  return start + (end - start) * progress;
}

function drawBudgetForFps() {
  if (state.fps > 0 && state.fps < 18) return 9000;
  if (state.fps > 0 && state.fps < 28) return 16000;
  return state.proceduralVehicles.length > 30000 ? state.targetDrawnVehicles : state.proceduralVehicles.length;
}

function trackFps(timestamp) {
  if (!state.lastFpsTimestamp) {
    state.lastFpsTimestamp = timestamp;
    return;
  }
  state.fpsFrames += 1;
  const elapsed = timestamp - state.lastFpsTimestamp;
  if (elapsed >= 500) {
    state.fps = Math.round((state.fpsFrames * 1000) / elapsed);
    state.fpsFrames = 0;
    state.lastFpsTimestamp = timestamp;
    updatePerformanceMetrics();
  }
}

function updatePerformanceMetrics() {
  els.fps.textContent = String(state.fps || 0);
  els.drawn.textContent = `${state.visibleVehicles} / ${state.drawnVehicles}`;
}

function updateSpeedMetrics() {
  if (!state.proceduralVehicles.length) {
    els.avgSpeed.textContent = "0 kph";
    els.maxSpeed.textContent = "0 kph";
    return;
  }
  let total = 0;
  let max = 0;
  let count = 0;
  const stride = Math.max(1, Math.ceil(state.proceduralVehicles.length / 5000));
  for (let index = 0; index < state.proceduralVehicles.length; index += stride) {
    const speed = Number(state.proceduralVehicles[index].currentSpeedKph || state.proceduralVehicles[index].speedKph || 0);
    total += speed;
    max = Math.max(max, speed);
    count += 1;
  }
  els.avgSpeed.textContent = `${Math.round(total / Math.max(count, 1))} kph`;
  els.maxSpeed.textContent = `${Math.round(max)} kph`;
}

function positiveModulo(value, modulo) {
  return ((value % modulo) + modulo) % modulo;
}

function parseTimeToMinute(value) {
  const [hours, minutes] = String(value || "00:00").split(":").map((part) => Number(part));
  return ((hours || 0) % 24) * 60 + (minutes || 0);
}

function minuteToTime(minute) {
  const normalized = positiveModulo(Math.round(minute), 24 * 60);
  return `${String(Math.floor(normalized / 60)).padStart(2, "0")}:${String(normalized % 60).padStart(2, "0")}`;
}

function currentSimulationMinute() {
  const autoMinutes = els.autoTime && els.autoTime.checked ? (state.proceduralElapsedSeconds * Number(els.timeSpeed.value || 1)) / 60 : 0;
  return positiveModulo(state.runStartMinute + autoMinutes, 24 * 60);
}

function eventEndTime(event) {
  return minuteToTime(parseTimeToMinute(event.startTime || event.start_time || "00:00") + Number(event.durationMinutes || event.duration_minutes || 1));
}

function isEventActive(event, minute) {
  if (event.enabled === false) return false;
  const start = parseTimeToMinute(event.startTime || event.start_time || "00:00");
  const duration = Math.max(1, Number(event.durationMinutes || event.duration_minutes || 1));
  const offset = positiveModulo(minute - start, 24 * 60);
  return offset >= 0 && offset < duration;
}

function deterministicJitter(text) {
  let hash = 0;
  for (let index = 0; index < String(text).length; index += 1) {
    hash = (hash * 31 + String(text).charCodeAt(index)) % 9973;
  }
  return (hash / 9973) * 0.04;
}

function escapeHtml(value) {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function distance(a, b) {
  const dy = b[0] - a[0];
  const dx = b[1] - a[1];
  return Math.sqrt(dx * dx + dy * dy);
}

function carIconDataUrl(color) {
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="44" height="28" viewBox="0 0 44 28"><rect x="3" y="8" width="38" height="14" rx="5" fill="${color}" stroke="white" stroke-width="3"/><rect x="14" y="4" width="16" height="10" rx="4" fill="${color}" stroke="white" stroke-width="3"/><circle cx="12" cy="23" r="3" fill="#1f2729"/><circle cx="32" cy="23" r="3" fill="#1f2729"/></svg>`;
  return `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`;
}
