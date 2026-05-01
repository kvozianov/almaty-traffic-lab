from __future__ import annotations

import asyncio
from dataclasses import asdict
import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .ai_policy import build_policy
from .analytics import (
    build_run_analytics,
    compare_simulations,
    export_research_report_html,
    export_metrics_json,
    export_road_loads_csv,
    graph_to_leaflet_roads,
    simulation_frames_to_leaflet,
    top_loaded_roads,
)
from .calibration import match_calibration_to_graph
from .config import app_config
from .demand import generate_vehicle_demand
from .graph_cache import list_presets, load_preset_graph
from .network import CityGraph
from .scenarios import (
    add_bypass_road,
    apply_accident,
    apply_weather_speed_reduction,
    close_road,
    close_road_for_repair,
    reduce_capacity,
    retime_traffic_signal,
)
from .simulation import TrafficSimulation
from .time_profiles import format_hhmm, list_time_profiles, load_time_profile, parse_hhmm
from .timeline import (
    ScenarioEvent,
    apply_active_events,
    attach_timeline_metadata,
    default_timeline_events,
    events_payload,
    generate_random_events,
    normalize_events,
)
from .traffic_providers import build_provider, list_provider_statuses
from .visualization import record_frames
from .zones import build_zone_index, load_zones, zones_payload
from .zones import load_od_matrix


STATIC_DIR = Path(__file__).parent / "web" / "static"
RUNS: dict[str, dict[str, Any]] = {}
SCENARIOS: dict[str, dict[str, Any]] = {}
TRAFFIC_IMPORTS: dict[str, str] = {"csv": "data/traffic_profiles/sample_almaty.csv"}
SCENARIO_PRESETS_PATH = Path("data/scenarios/almaty_report_scenarios.json")


class ScenarioRequest(BaseModel):
    type: str = Field(default="none")
    road_id: str | None = None
    capacity_factor: float = 0.3
    speed_factor: float = 0.45
    signal_delay_s: float = 60.0
    demand_surge: bool = False
    duration_minutes: int = 60
    start_time: str | None = None
    enabled: bool = True


class ScenarioEventRequest(BaseModel):
    id: str | None = None
    type: str = "accident"
    road_id: str | None = None
    start_time: str = "17:10"
    duration_minutes: int = 40
    enabled: bool = True
    capacity_factor: float = 0.35
    speed_factor: float = 0.45
    signal_delay_s: float = 60.0
    intensity: float = 1.0


class SimulationRequest(BaseModel):
    preset_id: str = "full_almaty"
    vehicles: int = Field(default=80, ge=1, le=100000)
    steps: int = Field(default=240, ge=1, le=3000)
    tick_seconds: int = Field(default=10, ge=1, le=120)
    seed: int = 7
    refresh_cache: bool = False
    compare: bool = True
    manual_time: str = "17:00"
    time_preset: str = "evening_peak"
    auto_time: bool = False
    time_speed_multiplier: float = 1.0
    policy: str = "heuristic"
    demand_mode: str = "random_roads"
    reroute_interval_ticks: int = Field(default=12, ge=0, le=1000)
    random_events: bool = False
    events: list[ScenarioEventRequest] = Field(default_factory=list)
    scenario: ScenarioRequest = Field(default_factory=ScenarioRequest)


class RoadParameterPatch(BaseModel):
    capacity: int | None = None
    max_speed_kph: float | None = None
    lanes: int | None = None
    road_class: str | None = None
    signal_delay_s: float | None = None


class TrafficImportRequest(BaseModel):
    provider: str = "csv"
    path: str = "data/traffic_profiles/sample_almaty.csv"


def create_app() -> FastAPI:
    app = FastAPI(title="Almaty Traffic Simulation Dashboard")
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    @app.get("/api/presets")
    def presets() -> dict[str, object]:
        return {"presets": list_presets()}

    @app.get("/api/config")
    def config() -> dict[str, object]:
        return app_config()

    @app.get("/api/time-profiles")
    def time_profiles() -> dict[str, object]:
        profile = load_time_profile()
        return {"profiles": list_time_profiles(), "active": profile.name, "periods": profile.periods, "corridors": profile.corridors}

    @app.get("/api/time-presets")
    def time_presets() -> dict[str, object]:
        return {"presets": _time_presets()}

    @app.get("/api/zones")
    def zones() -> dict[str, object]:
        loaded = load_zones()
        return {"zones": zones_payload(loaded)}

    @app.get("/api/scenario-presets")
    def scenario_presets() -> dict[str, object]:
        return {"presets": _load_scenario_presets()}

    @app.get("/api/calibration-layer")
    def calibration_layer(preset_id: str = "full_almaty_fast") -> dict[str, object]:
        graph = load_preset_graph(preset_id)
        return {"presetId": preset_id, "layer": match_calibration_to_graph(graph)}

    @app.post("/api/policies/select-destinations")
    def select_destinations(request: SimulationRequest) -> dict[str, object]:
        graph = load_preset_graph(request.preset_id, refresh=request.refresh_cache)
        policy = build_policy(request.policy)
        minute = parse_hhmm(request.manual_time)
        decisions = []
        import random

        rng = random.Random(request.seed)
        for index in range(min(request.vehicles, 100)):
            decision = policy.choose_trip(graph, rng, road_loads={}, minute_of_day=minute)
            decisions.append(
                {
                    "vehicleId": f"car-{index + 1}",
                    "startNode": decision.start_node,
                    "destinationNode": decision.destination_node,
                    "behavior": decision.behavior,
                    "spawnRoadId": decision.spawn_road_id,
                    "spawnRatio": decision.spawn_ratio,
                }
            )
        return {"minuteOfDay": minute, "time": format_hhmm(minute), "decisions": decisions}

    @app.post("/api/scenarios")
    def create_scenario(scenario: ScenarioRequest) -> dict[str, object]:
        scenario_id = str(uuid4())
        SCENARIOS[scenario_id] = scenario.model_dump()
        return {"id": scenario_id, "scenario": SCENARIOS[scenario_id]}

    @app.patch("/api/scenarios/{scenario_id}")
    def update_scenario(scenario_id: str, scenario: ScenarioRequest) -> dict[str, object]:
        if scenario_id not in SCENARIOS:
            raise HTTPException(status_code=404, detail=f"Unknown scenario id: {scenario_id}")
        SCENARIOS[scenario_id] = scenario.model_dump()
        return {"id": scenario_id, "scenario": SCENARIOS[scenario_id]}

    @app.delete("/api/scenarios/{scenario_id}")
    def delete_scenario(scenario_id: str) -> dict[str, object]:
        removed = SCENARIOS.pop(scenario_id, None)
        return {"id": scenario_id, "deleted": removed is not None}

    @app.get("/api/roads/{road_id:path}")
    def get_road(road_id: str, preset_id: str = "full_almaty_fast") -> dict[str, object]:
        graph = load_preset_graph(preset_id)
        if road_id not in graph.roads:
            raise HTTPException(status_code=404, detail=f"Unknown road id: {road_id}")
        return {"road": _road_payload(graph, road_id)}

    @app.get("/api/signals")
    def get_signals(preset_id: str = "full_almaty_fast") -> dict[str, object]:
        graph = load_preset_graph(preset_id)
        return {"signals": [_signal_payload(signal) for signal in graph.signals.values()]}

    @app.patch("/api/roads/{road_id:path}/parameters")
    def update_road_parameters(road_id: str, patch: RoadParameterPatch, preset_id: str = "full_almaty_fast") -> dict[str, object]:
        graph = load_preset_graph(preset_id)
        if road_id not in graph.roads:
            raise HTTPException(status_code=404, detail=f"Unknown road id: {road_id}")
        road = graph.roads[road_id]
        if patch.capacity is not None:
            road.capacity = patch.capacity
        if patch.max_speed_kph is not None:
            road.max_speed_kph = patch.max_speed_kph
        if patch.lanes is not None:
            road.lanes = patch.lanes
        if patch.road_class is not None:
            road.road_class = patch.road_class
        if patch.signal_delay_s is not None:
            road.signal_delay_s = patch.signal_delay_s
        return {"road": _road_payload(graph, road_id)}

    @app.get("/api/traffic/providers")
    def traffic_providers() -> dict[str, object]:
        return {"providers": list_provider_statuses()}

    @app.post("/api/traffic/import")
    def import_traffic(request: TrafficImportRequest) -> dict[str, object]:
        provider = build_provider(request.provider, request.path)
        status = provider.status()
        if request.provider == "csv":
            if not status.get("available"):
                raise HTTPException(status_code=400, detail=f"CSV file does not exist: {request.path}")
            TRAFFIC_IMPORTS["csv"] = request.path
        return {"provider": status, "message": "Provider configured. External raw traffic is not scraped or redistributed."}

    @app.get("/api/statistics/road/{road_id:path}")
    def road_statistics(road_id: str, provider_id: str = "synthetic") -> dict[str, object]:
        provider = build_provider(provider_id, TRAFFIC_IMPORTS.get(provider_id))
        observations = provider.observations_for_road(road_id)
        return {"roadId": road_id, "provider": provider.status(), "observations": [asdict(ob) for ob in observations]}

    @app.get("/api/statistics/corridor/{name}")
    def corridor_statistics(name: str, provider_id: str = "synthetic") -> dict[str, object]:
        provider = build_provider(provider_id, TRAFFIC_IMPORTS.get(provider_id))
        observations = provider.observations_for_road(name)
        return {"corridor": name, "provider": provider.status(), "observations": [asdict(ob) for ob in observations]}

    @app.post("/api/simulations")
    def create_simulation(request: SimulationRequest) -> dict[str, object]:
        try:
            result = _run_request(request)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        RUNS[result["id"]] = result
        return _run_metadata(result)

    @app.post("/api/preview")
    def create_preview(request: SimulationRequest) -> dict[str, object]:
        try:
            result = _run_preview(request)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        RUNS[result["id"]] = result
        return _run_metadata(result)

    @app.get("/api/simulations/{run_id}")
    def get_simulation(run_id: str) -> dict[str, object]:
        return _run_metadata(_get_run(run_id))

    @app.get("/api/simulations/{run_id}/frames")
    def get_frames(run_id: str) -> dict[str, object]:
        run = _get_run(run_id)
        return {
            "id": run_id,
            "roads": run["roads"],
            "scenarioRoads": run["scenario_roads"],
            "events": run.get("events", []),
            "zones": run.get("zones", []),
            "calibrationLayer": run.get("calibrationLayer"),
            "frames": run["frames"],
            "procedural": run.get("procedural", False),
            "proceduralVehicles": run.get("procedural_vehicles", []),
            "baselineFrames": run.get("baseline_frames"),
            "comparison": run.get("comparison"),
        }

    @app.get("/api/simulations/{run_id}/analytics")
    def get_analytics(run_id: str) -> dict[str, object]:
        run = _get_run(run_id)
        analytics = run.get("analytics")
        if analytics is None:
            analytics = build_run_analytics(run)
            run["analytics"] = analytics
        return {"id": run_id, "analytics": analytics}

    @app.get("/api/simulations/{run_id}/export/metrics")
    def export_metrics(run_id: str) -> dict[str, str]:
        run = _get_run(run_id)
        path = export_metrics_json(Path("reports") / f"{run_id}-metrics.json", _run_metadata(run))
        return {"path": str(path.resolve())}

    @app.get("/api/simulations/{run_id}/export/road-loads")
    def export_road_loads(run_id: str) -> dict[str, str]:
        run = _get_run(run_id)
        if run["scenario_sim"] is None:
            raise HTTPException(status_code=400, detail="Road-load CSV export is available for full simulations, not fast previews.")
        path = export_road_loads_csv(Path("reports") / f"{run_id}-road-loads.csv", run["scenario_sim"])
        return {"path": str(path.resolve())}

    @app.get("/api/simulations/{run_id}/export/report")
    def export_report(run_id: str) -> dict[str, str]:
        run = _get_run(run_id)
        analytics = run.get("analytics") or build_run_analytics(run)
        run["analytics"] = analytics
        path = export_research_report_html(Path("reports") / f"{run_id}-research-report.html", run, analytics)
        return {"path": str(path.resolve())}

    @app.websocket("/ws/simulations/{run_id}")
    async def stream_simulation(websocket: WebSocket, run_id: str) -> None:
        await websocket.accept()
        run = _get_run(run_id)
        try:
            for frame in run["frames"]:
                await websocket.send_json({"type": "frame", "frame": frame})
                await asyncio.sleep(0.05)
            await websocket.send_json({"type": "done", "stats": run["stats"]})
        except WebSocketDisconnect:
            return

    return app


app = create_app()


def _run_request(request: SimulationRequest) -> dict[str, Any]:
    baseline_graph = load_preset_graph(request.preset_id, refresh=request.refresh_cache)
    scenario_graph = load_preset_graph(request.preset_id, refresh=False)
    manual_time = _effective_time(request)
    minute = parse_hhmm(manual_time)
    events = _events_for_request(request, scenario_graph, manual_time)
    attach_timeline_metadata(scenario_graph, events)
    scenario_roads = _apply_scenario_request(scenario_graph, request.scenario, manual_time)
    scenario_roads = sorted(set(scenario_roads + apply_active_events(scenario_graph, events, minute)))

    profile = load_time_profile()
    horizon_s = request.steps * request.tick_seconds * 0.65 * profile.demand_multiplier(minute)
    surge_node = _scenario_node(scenario_graph, scenario_roads[0]) if request.scenario.demand_surge and scenario_roads else None
    baseline_sim = _build_simulation(baseline_graph, request, horizon_s=horizon_s, manual_time=manual_time)
    scenario_sim = _build_simulation(scenario_graph, request, horizon_s=horizon_s, surge_node=surge_node, manual_time=manual_time)

    baseline_frames = record_frames(baseline_sim, request.steps) if request.compare else []
    scenario_frames = record_frames(scenario_sim, request.steps)
    comparison = compare_simulations(baseline_sim, scenario_sim) if request.compare else None
    roads = graph_to_leaflet_roads(scenario_graph, scenario_sim.peak_road_loads(), max_roads=None)
    calibration_layer = match_calibration_to_graph(scenario_graph)
    run_id = str(uuid4())

    stats = asdict(scenario_sim.summary())
    stats["time"] = format_hhmm(minute)
    stats["demand_multiplier"] = profile.demand_multiplier(minute)
    stats["reroutes"] = sum(vehicle.reroutes for vehicle in scenario_sim.vehicles.values())
    baseline_stats = asdict(baseline_sim.summary()) if request.compare else None
    if baseline_stats is not None:
        baseline_stats["time"] = format_hhmm(minute)
        baseline_stats["demand_multiplier"] = profile.demand_multiplier(minute)
        baseline_stats["reroutes"] = sum(vehicle.reroutes for vehicle in baseline_sim.vehicles.values())

    result = {
        "id": run_id,
        "request": request.model_dump(),
        "presetId": request.preset_id,
        "roads": roads,
        "scenario_roads": scenario_roads,
        "frames": simulation_frames_to_leaflet(scenario_sim, scenario_frames),
        "baseline_frames": simulation_frames_to_leaflet(baseline_sim, baseline_frames) if baseline_frames else None,
        "stats": stats,
        "baseline_stats": baseline_stats,
        "comparison": comparison,
        "hot_roads": top_loaded_roads(scenario_sim),
        "scenario_sim": scenario_sim,
        "events": events_payload(events, minute),
        "zones": zones_payload(load_zones()) if request.demand_mode == "od_zones" else [],
        "calibrationLayer": calibration_layer,
    }
    result["analytics"] = build_run_analytics(result)
    return result


def _run_preview(request: SimulationRequest) -> dict[str, Any]:
    graph = load_preset_graph(request.preset_id, refresh=request.refresh_cache)
    manual_time = _effective_time(request)
    minute = parse_hhmm(manual_time)
    events = _events_for_request(request, graph, manual_time)
    timeline_roads = attach_timeline_metadata(graph, events)
    scenario_roads = _apply_scenario_request(graph, request.scenario, manual_time)
    scenario_roads = sorted(set(scenario_roads + apply_active_events(graph, events, minute) + timeline_roads))
    selected_roads = [road for road in graph.roads.values() if road.is_open and len(graph.road_geometry(road.road_id)) >= 2]
    selected_roads.sort(key=lambda road: road.road_id)
    zones = load_zones() if request.demand_mode == "od_zones" else []
    zone_index = build_zone_index(graph, zones, limit=120) if zones else None
    od_matrix = load_od_matrix() if zones else None
    vehicle_paths = _build_preview_vehicle_paths(
        graph,
        selected_roads,
        request.vehicles,
        request.seed,
        manual_time,
        request.demand_mode,
        zones,
        zone_index,
        request.time_preset,
        od_matrix,
    )
    run_id = str(uuid4())
    road_counts: dict[str, int] = {road.road_id: 0 for road in selected_roads}
    for path in vehicle_paths:
        route_ids = path.get("routeRoadIds") if isinstance(path.get("routeRoadIds"), list) else [path["roadId"]]
        for route_index, route_road_id in enumerate(route_ids[:12]):
            if route_road_id in road_counts:
                road_counts[route_road_id] = road_counts.get(route_road_id, 0) + (1 if route_index == 0 else 0.35)
    road_loads = {
        road.road_id: min(1.5, road_counts.get(road.road_id, 0) / max(road.effective_capacity(), 1))
        for road in selected_roads
    }
    for road_id in scenario_roads:
        road_loads[road_id] = 1.0
    leaflet_roads = graph_to_leaflet_roads(graph, road_loads, max_roads=None)
    calibration_layer = match_calibration_to_graph(graph)
    _attach_preview_next_roads(graph, leaflet_roads, seed=request.seed)
    profile = load_time_profile()
    stats = {
        "tick": request.steps,
        "sim_time_s": request.steps * request.tick_seconds,
        "active_vehicles": request.vehicles,
        "arrived_vehicles": 0,
        "stuck_vehicles": 0,
        "average_trip_time_s": 0.0,
        "max_road_load": max(road_loads.values(), default=0.0),
        "average_road_load": sum(road_loads.values()) / len(road_loads) if road_loads else 0.0,
        "time": format_hhmm(minute),
        "demand_multiplier": profile.demand_multiplier(minute),
        "reroutes": 0,
    }
    result = {
        "id": run_id,
        "request": request.model_dump(),
        "presetId": request.preset_id,
        "roads": leaflet_roads,
        "scenario_roads": scenario_roads,
        "frames": [{"tick": 0, "simTimeS": 0, "vehicles": []}],
        "procedural": True,
        "procedural_vehicles": vehicle_paths,
        "baseline_frames": None,
        "stats": stats,
        "baseline_stats": None,
        "comparison": None,
        "hot_roads": [
            {"roadId": road_id, "load": load}
            for road_id, load in sorted(road_loads.items(), key=lambda item: item[1], reverse=True)[:8]
        ],
        "scenario_sim": None,
        "events": events_payload(events, minute),
        "zones": zones_payload(zones),
        "calibrationLayer": calibration_layer,
    }
    result["analytics"] = build_run_analytics(result)
    return result


def _attach_preview_next_roads(graph: CityGraph, leaflet_roads: list[dict[str, object]], seed: int) -> None:
    import random

    rng = random.Random(seed + 137)
    open_road_ids = {road["id"] for road in leaflet_roads if road.get("isOpen")}
    fallback_roads = sorted(open_road_ids)
    next_by_road: dict[str, str] = {}
    candidates_by_road: dict[str, list[str]] = {}
    for road_id in fallback_roads:
        road = graph.roads[road_id]
        candidates = [
            candidate_id
            for candidate_id in graph.outgoing.get(road.end_node, [])
            if candidate_id in open_road_ids and graph.roads[candidate_id].is_open
        ]
        if candidates:
            candidates.sort(key=lambda candidate_id: (graph.roads[candidate_id].road_class, graph.roads[candidate_id].length_m))
            shortlist = candidates[: min(len(candidates), 8)]
            candidates_by_road[road_id] = shortlist
            next_by_road[road_id] = rng.choice(shortlist[: min(len(shortlist), 5)])
        else:
            next_by_road[road_id] = rng.choice(fallback_roads) if fallback_roads else road_id
            candidates_by_road[road_id] = [next_by_road[road_id]]

    for road in leaflet_roads:
        road["nextRoadId"] = next_by_road.get(str(road["id"]), road["id"])
        road["nextRoadCandidates"] = candidates_by_road.get(str(road["id"]), [road["nextRoadId"]])


def _build_preview_vehicle_paths(
    graph: CityGraph,
    roads: list[Any],
    vehicle_count: int,
    seed: int,
    manual_time: str,
    demand_mode: str = "random_roads",
    zones: list[Any] | None = None,
    zone_index: dict[str, dict[str, list[str]]] | None = None,
    time_preset: str | None = None,
    od_matrix: dict[str, dict[str, float]] | None = None,
) -> list[dict[str, object]]:
    import random

    rng = random.Random(seed)
    profile = load_time_profile()
    minute = parse_hhmm(manual_time)
    usable_roads = [road for road in roads if road.is_open and len(graph.road_geometry(road.road_id)) >= 2]
    if not usable_roads:
        raise ValueError("No roads available for preview")
    min_route_roads = 4 if len(usable_roads) < 80 else 12 if len(usable_roads) < 5000 else 18
    max_route_roads = 18 if len(usable_roads) < 80 else 48 if len(usable_roads) < 5000 else 72
    template_count = min(len(usable_roads), max(128, min(vehicle_count, vehicle_count // 4 + 128, 2400)))
    route_templates = _build_preview_route_templates(
        graph,
        usable_roads,
        template_count,
        rng,
        demand_mode,
        zones,
        zone_index,
        minute,
        time_preset,
        od_matrix,
        min_route_roads,
        max_route_roads,
    )
    if not route_templates:
        raise ValueError("Could not generate route templates for preview")
    vehicles: list[dict[str, object]] = []
    for index in range(vehicle_count):
        template = route_templates[index % len(route_templates)]
        road = graph.roads[str(template["roadId"])]
        route_road_ids = list(template["routeRoadIds"])
        destination_node = template.get("destinationNode")
        origin_zone = template.get("originZone")
        destination_zone = template.get("destinationZone")
        time_speed = profile.speed_multiplier_for_road(road, minute)
        visible_speed = max(0.00004, min(0.0012, (road.max_speed_kph / 50.0) * road.speed_modifier * time_speed * rng.uniform(0.00022, 0.00062)))
        speed_kph = max(3.0, road.max_speed_kph * road.speed_modifier * time_speed * rng.uniform(0.72, 1.08))
        vehicles.append(
            {
                "roadId": road.road_id,
                "offset": rng.random(),
                "speed": visible_speed,
                "speedKph": round(speed_kph, 1),
                "state": "moving",
                "routeRoadIds": route_road_ids,
                "routeIndex": 0,
                "destinationNode": destination_node,
                "originZone": origin_zone,
                "destinationZone": destination_zone,
            }
        )
    return vehicles


def _build_preview_route_templates(
    graph: CityGraph,
    usable_roads: list[Any],
    template_count: int,
    rng: Any,
    demand_mode: str,
    zones: list[Any] | None,
    zone_index: dict[str, dict[str, list[str]]] | None,
    minute: int,
    time_preset: str | None,
    od_matrix: dict[str, dict[str, float]] | None,
    min_route_roads: int,
    max_route_roads: int,
) -> list[dict[str, object]]:
    start_roads = _distributed_start_roads(graph, usable_roads, max(template_count * 2, template_count + 48), rng)
    templates: list[dict[str, object]] = []
    for start_road in start_roads:
        origin_zone_id = None
        destination_zone_id = None
        destination_nodes: list[str] = []
        if demand_mode == "od_zones" and zones and zone_index:
            origin_zone = _nearest_zone_for_road(graph, start_road, zones)
            destination_zone = _choose_destination_zone_for_origin(origin_zone, zones, rng, minute, time_preset, od_matrix)
            origin_zone_id = origin_zone.zone_id
            destination_zone_id = destination_zone.zone_id
            destination_nodes = list(zone_index.get(destination_zone.zone_id, {}).get("nodes", []))
        else:
            destination_nodes = _far_destination_nodes(graph, start_road, usable_roads, rng, limit=36)
        destination_node, route_road_ids = _choose_long_route_from_road(
            graph,
            start_road,
            destination_nodes,
            rng,
            min_route_roads=min_route_roads,
            max_route_roads=max_route_roads,
        )
        if len(route_road_ids) < min_route_roads:
            continue
        templates.append(
            {
                "roadId": start_road.road_id,
                "routeRoadIds": route_road_ids,
                "destinationNode": destination_node,
                "originZone": origin_zone_id,
                "destinationZone": destination_zone_id,
            }
        )
        if len(templates) >= template_count:
            break
    if len(templates) < template_count:
        relaxed_min = max(4, min_route_roads // 2)
        for start_road in start_roads:
            if any(item["roadId"] == start_road.road_id for item in templates):
                continue
            destination_nodes = _far_destination_nodes(graph, start_road, usable_roads, rng, limit=24)
            destination_node, route_road_ids = _choose_long_route_from_road(
                graph,
                start_road,
                destination_nodes,
                rng,
                min_route_roads=relaxed_min,
                max_route_roads=max_route_roads,
            )
            if len(route_road_ids) < relaxed_min:
                continue
            templates.append(
                {
                    "roadId": start_road.road_id,
                    "routeRoadIds": route_road_ids,
                    "destinationNode": destination_node,
                    "originZone": None,
                    "destinationZone": None,
                }
            )
            if len(templates) >= template_count:
                break
    rng.shuffle(templates)
    return templates


def _choose_long_route_from_road(
    graph: CityGraph,
    start_road: Any,
    destination_nodes: list[str],
    rng: Any,
    min_route_roads: int,
    max_route_roads: int,
) -> tuple[str | None, list[str]]:
    nodes = [node_id for node_id in destination_nodes if node_id in graph.nodes]
    if not nodes:
        return None, [start_road.road_id]
    rng.shuffle(nodes)
    best_destination = None
    best_route = [start_road.road_id]
    for destination_node in nodes[:36]:
        if destination_node == start_road.end_node:
            continue
        route_ids = _greedy_preview_route(graph, start_road.road_id, destination_node, max_roads=max_route_roads)
        if len(route_ids) > len(best_route):
            best_destination = destination_node
            best_route = route_ids
        if len(route_ids) >= min_route_roads:
            return destination_node, route_ids
    return best_destination, best_route


def _distributed_start_roads(graph: CityGraph, usable_roads: list[Any], template_count: int, rng: Any) -> list[Any]:
    def key(road: Any) -> tuple[float, float, str]:
        lng, lat = _road_midpoint(graph, road.road_id)
        return lat, lng, road.road_id

    sorted_roads = sorted(usable_roads, key=key)
    if template_count >= len(sorted_roads):
        shuffled = list(sorted_roads)
        rng.shuffle(shuffled)
        return shuffled
    stride = max(1, len(sorted_roads) // template_count)
    sampled = sorted_roads[::stride][:template_count]
    if len(sampled) < template_count:
        sampled = list(sampled)
        remaining = [road for road in sorted_roads if road not in sampled]
        rng.shuffle(remaining)
        sampled.extend(remaining[: template_count - len(sampled)])
    else:
        alternating = sampled[::2] + sampled[1::2]
        sampled = alternating[:template_count]
    return sampled


def _nearest_zone_for_road(graph: CityGraph, road: Any, zones: list[Any]) -> Any:
    lng, lat = _road_midpoint(graph, road.road_id)
    return min(zones, key=lambda zone: (zone.lat - lat) ** 2 + (zone.lng - lng) ** 2)


def _choose_destination_zone_for_origin(
    origin_zone: Any,
    zones: list[Any],
    rng: Any,
    minute: int,
    time_preset: str | None,
    od_matrix: dict[str, dict[str, float]] | None,
) -> Any:
    from .zones import time_period_for_minute

    period = time_period_for_minute(minute, time_preset)
    candidates = [zone for zone in zones if zone.zone_id != origin_zone.zone_id]
    weights = []
    for zone in candidates:
        base = zone.weight_for_period(period)
        if od_matrix:
            base *= float(od_matrix.get(origin_zone.zone_id, {}).get(zone.zone_id, 1.0))
        weights.append(max(0.05, base))
    return rng.choices(candidates, weights=weights, k=1)[0]


def _far_destination_nodes(graph: CityGraph, start_road: Any, usable_roads: list[Any], rng: Any, limit: int = 36) -> list[str]:
    start_lng, start_lat = _road_midpoint(graph, start_road.road_id)
    ranked = sorted(
        usable_roads,
        key=lambda road: -((_road_midpoint(graph, road.road_id)[0] - start_lng) ** 2 + (_road_midpoint(graph, road.road_id)[1] - start_lat) ** 2),
    )
    candidates = [road.end_node for road in ranked if road.road_id != start_road.road_id]
    shortlist = candidates[: max(limit * 2, limit)]
    rng.shuffle(shortlist)
    return shortlist[:limit]


def _road_midpoint(graph: CityGraph, road_id: str) -> tuple[float, float]:
    geometry = graph.road_geometry(road_id)
    lng = sum(point[0] for point in geometry) / len(geometry)
    lat = sum(point[1] for point in geometry) / len(geometry)
    return lng, lat


def _greedy_preview_route(graph: CityGraph, start_road_id: str, destination_node: str, max_roads: int = 24) -> list[str]:
    if start_road_id not in graph.roads or destination_node not in graph.nodes:
        return []
    route = [start_road_id]
    current_node = graph.roads[start_road_id].end_node
    visited_nodes = {graph.roads[start_road_id].start_node, current_node}
    for _ in range(max_roads - 1):
        if current_node == destination_node:
            break
        candidates = [graph.roads[road_id] for road_id in graph.outgoing.get(current_node, []) if graph.roads[road_id].is_open]
        if not candidates:
            break
        candidates.sort(
            key=lambda road: (
                road.end_node in visited_nodes,
                _node_distance_sq(graph, road.end_node, destination_node),
                -road.max_speed_kph,
                road.length_m,
            )
        )
        chosen = candidates[0]
        if chosen.end_node in visited_nodes and len(candidates) > 1:
            chosen = candidates[1]
        route.append(chosen.road_id)
        current_node = chosen.end_node
        visited_nodes.add(current_node)
        if current_node == destination_node:
            break
    return route


def _node_distance_sq(graph: CityGraph, node_id: str, destination_node: str) -> float:
    node = graph.nodes[node_id]
    target = graph.nodes[destination_node]
    return (node.x - target.x) ** 2 + (node.y - target.y) ** 2


def _build_preview_frames(graph: CityGraph, roads: list[Any], vehicle_count: int, steps: int, seed: int) -> list[dict[str, object]]:
    import random

    rng = random.Random(seed)
    usable_roads = [road for road in roads if road.is_open and len(graph.road_geometry(road.road_id)) >= 2]
    if not usable_roads:
        raise ValueError("No roads available for preview")
    assignments = [
        {
            "id": f"car-{index + 1}",
            "road": rng.choice(usable_roads),
            "offset": rng.random(),
            "speed": rng.uniform(0.0015, 0.0045),
        }
        for index in range(vehicle_count)
    ]
    frames: list[dict[str, object]] = []
    for tick in range(steps + 1):
        vehicles = []
        for assignment in assignments:
            ratio = (assignment["offset"] + assignment["speed"] * tick) % 1.0
            x, y = _point_on_road(graph, assignment["road"].road_id, ratio)
            vehicles.append({"id": assignment["id"], "lat": y, "lng": x, "state": "moving"})
        frames.append({"tick": tick, "simTimeS": tick * 10, "vehicles": vehicles})
    return frames


def _point_on_road(graph: CityGraph, road_id: str, ratio: float) -> tuple[float, float]:
    from .visualization import _interpolate_polyline

    return _interpolate_polyline(graph.road_geometry(road_id), ratio)


def _build_simulation(
    graph: CityGraph,
    request: SimulationRequest,
    horizon_s: float,
    manual_time: str,
    surge_node: str | None = None,
) -> TrafficSimulation:
    sim = TrafficSimulation(
        graph=graph,
        tick_seconds=request.tick_seconds,
        routing_algorithm="astar",
        manual_time=manual_time,
        auto_time=request.auto_time,
        time_speed_multiplier=request.time_speed_multiplier,
        time_profile=load_time_profile(),
        reroute_interval_ticks=request.reroute_interval_ticks,
    )
    zones = load_zones() if request.demand_mode == "od_zones" else None
    vehicles = generate_vehicle_demand(
        graph,
        request.vehicles,
        seed=request.seed,
        horizon_s=horizon_s,
        surge_node=surge_node,
        policy=build_policy(request.policy),
        minute_of_day=parse_hhmm(manual_time),
        demand_mode=request.demand_mode,
        zones=zones,
        time_preset=request.time_preset,
    )
    for vehicle in vehicles:
        sim.add_vehicle(vehicle)
    return sim


def _apply_scenario_request(graph: CityGraph, scenario: ScenarioRequest, manual_time: str = "17:00") -> list[str]:
    if scenario.type == "none" or not scenario.enabled:
        return []
    start_time = scenario.start_time or manual_time
    if not ScenarioEvent("single", scenario.type, scenario.road_id, start_time, scenario.duration_minutes).active_at(parse_hhmm(manual_time)):
        return []
    road_id = scenario.road_id if scenario.road_id in graph.roads else _pick_representative_road(graph)
    if scenario.type == "accident":
        apply_accident(graph, road_id, capacity_factor=scenario.capacity_factor, speed_factor=scenario.speed_factor)
    elif scenario.type == "repair":
        close_road_for_repair(graph, road_id)
    elif scenario.type == "closure":
        close_road(graph, road_id)
    elif scenario.type == "capacity_reduction":
        reduce_capacity(graph, road_id, scenario.capacity_factor)
    elif scenario.type == "signal":
        retime_traffic_signal(graph, road_id, new_delay_s=scenario.signal_delay_s)
    elif scenario.type == "weather":
        apply_weather_speed_reduction(graph, scenario.speed_factor)
        return list(graph.roads)[:25]
    elif scenario.type == "demand_surge":
        scenario.demand_surge = True
        graph.roads[road_id].metadata["scenario"] = "demand_surge"
    elif scenario.type == "new-road":
        start = graph.roads[road_id].start_node
        end = graph.roads[road_id].end_node
        add_bypass_road(
            graph,
            road_id=f"scenario_bypass_{road_id}",
            start_node=start,
            end_node=end,
            length_m=max(graph.roads[road_id].length_m * 0.7, 50.0),
            max_speed_kph=max(graph.roads[road_id].max_speed_kph, 60.0),
            capacity=max(graph.roads[road_id].capacity * 2, 24),
            signal_delay_s=0,
        )
        return [road_id, f"scenario_bypass_{road_id}"]
    else:
        raise ValueError(f"Unsupported scenario type: {scenario.type}")
    return [road_id]


def _effective_time(request: SimulationRequest) -> str:
    preset = next((item for item in _time_presets() if item["id"] == request.time_preset), None)
    if preset and request.time_preset != "manual":
        return str(preset["time"])
    return request.manual_time or "17:00"


def _events_for_request(request: SimulationRequest, graph: CityGraph, manual_time: str) -> list[ScenarioEvent]:
    events = normalize_events(request.events)
    duration_minutes = max(1, int(request.steps * request.tick_seconds / 60))
    if request.random_events:
        events.extend(generate_random_events(graph, request.seed, duration_minutes=duration_minutes, start_time=manual_time))
    return events


def _time_presets() -> list[dict[str, object]]:
    return [
        {"id": "manual", "name": "Manual", "time": None, "profile": "manual"},
        {"id": "morning_peak", "name": "Morning peak", "time": "08:00", "profile": "weekday"},
        {"id": "lunch", "name": "Lunch", "time": "13:00", "profile": "weekday"},
        {"id": "evening_peak", "name": "Evening peak", "time": "17:00", "profile": "weekday"},
        {"id": "night", "name": "Night", "time": "23:00", "profile": "weekday"},
        {"id": "weekend", "name": "Weekend", "time": "11:00", "profile": "weekend"},
    ]


def _load_scenario_presets() -> list[dict[str, object]]:
    payload = json.loads(SCENARIO_PRESETS_PATH.read_text(encoding="utf-8"))
    return list(payload.get("presets", []))


def _pick_representative_road(graph: CityGraph) -> str:
    return max(graph.roads, key=lambda road_id: graph.roads[road_id].length_m)


def _scenario_node(graph: CityGraph, road_id: str) -> str | None:
    if road_id not in graph.roads:
        return None
    return graph.roads[road_id].start_node


def _road_payload(graph: CityGraph, road_id: str) -> dict[str, object]:
    road = graph.roads[road_id]
    signal_node_ids = list(road.metadata.get("signal_node_ids", []))
    return {
        "id": road_id,
        "name": road.metadata.get("name") or road_id,
        "startNode": road.start_node,
        "endNode": road.end_node,
        "lengthM": road.length_m,
        "capacity": road.capacity,
        "effectiveCapacity": road.effective_capacity(),
        "maxSpeedKph": road.max_speed_kph,
        "estimatedSpeedKph": road.effective_speed_kph(0),
        "speedSource": road.metadata.get("speed_source", "maxspeed_fallback"),
        "rawMaxspeed": road.metadata.get("raw_maxspeed"),
        "lanes": road.lanes,
        "lanesSource": road.metadata.get("lanes_source", "lanes_fallback"),
        "rawLanes": road.metadata.get("raw_lanes"),
        "roadClass": road.road_class,
        "signalDelayS": road.signal_delay_s,
        "signalCount": int(road.metadata.get("signal_count", 0) or 0),
        "signalNodeIds": signal_node_ids,
        "isOpen": road.is_open,
        "geometry": graph.road_geometry(road_id),
        "metadata": road.metadata,
    }


def _signal_payload(signal: Any) -> dict[str, object]:
    return {
        "id": signal.signal_id,
        "nodeId": signal.node_id,
        "lat": signal.lat,
        "lng": signal.lng,
        "cycleS": signal.cycle_s,
        "greenS": signal.green_s,
        "yellowS": signal.yellow_s,
        "redS": signal.red_s,
        "delayS": signal.delay_s,
    }


def _run_metadata(run: dict[str, Any]) -> dict[str, object]:
    return {
        "id": run["id"],
        "presetId": run["presetId"],
        "request": run["request"],
        "stats": run["stats"],
        "baselineStats": run.get("baseline_stats"),
        "comparison": run.get("comparison"),
        "hotRoads": run["hot_roads"],
        "scenarioRoads": run["scenario_roads"],
        "events": run.get("events", []),
        "procedural": run.get("procedural", False),
        "frameCount": len(run["frames"]),
        "roadCount": len(run["roads"]),
    }


def _get_run(run_id: str) -> dict[str, Any]:
    if run_id not in RUNS:
        raise HTTPException(status_code=404, detail=f"Unknown simulation id: {run_id}")
    return RUNS[run_id]
