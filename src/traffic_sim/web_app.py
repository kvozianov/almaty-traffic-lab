from __future__ import annotations

import asyncio
from dataclasses import asdict
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .ai_policy import build_policy
from .analytics import (
    compare_simulations,
    export_metrics_json,
    export_road_loads_csv,
    graph_to_leaflet_roads,
    simulation_frames_to_leaflet,
    top_loaded_roads,
)
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
from .traffic_providers import build_provider, list_provider_statuses
from .visualization import record_frames


STATIC_DIR = Path(__file__).parent / "web" / "static"
RUNS: dict[str, dict[str, Any]] = {}
SCENARIOS: dict[str, dict[str, Any]] = {}
TRAFFIC_IMPORTS: dict[str, str] = {"csv": "data/traffic_profiles/sample_almaty.csv"}


class ScenarioRequest(BaseModel):
    type: str = Field(default="none")
    road_id: str | None = None
    capacity_factor: float = 0.3
    speed_factor: float = 0.45
    signal_delay_s: float = 60.0
    demand_surge: bool = False
    duration_minutes: int = 60


class SimulationRequest(BaseModel):
    preset_id: str = "full_almaty"
    vehicles: int = Field(default=80, ge=1, le=100000)
    steps: int = Field(default=240, ge=1, le=3000)
    tick_seconds: int = Field(default=10, ge=1, le=120)
    seed: int = 7
    refresh_cache: bool = False
    compare: bool = True
    manual_time: str = "17:00"
    auto_time: bool = False
    time_speed_multiplier: float = 1.0
    policy: str = "heuristic"
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
        road = graph.roads[road_id]
        return {"road": _road_payload(graph, road_id)}

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
            "frames": run["frames"],
            "procedural": run.get("procedural", False),
            "proceduralVehicles": run.get("procedural_vehicles", []),
            "baselineFrames": run.get("baseline_frames"),
            "comparison": run.get("comparison"),
        }

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
    scenario_roads = _apply_scenario_request(scenario_graph, request.scenario)

    profile = load_time_profile()
    horizon_s = request.steps * request.tick_seconds * 0.65 * profile.demand_multiplier(parse_hhmm(request.manual_time))
    surge_node = _scenario_node(scenario_graph, scenario_roads[0]) if request.scenario.demand_surge and scenario_roads else None
    baseline_sim = _build_simulation(baseline_graph, request, horizon_s=horizon_s)
    scenario_sim = _build_simulation(scenario_graph, request, horizon_s=horizon_s, surge_node=surge_node)

    baseline_frames = record_frames(baseline_sim, request.steps) if request.compare else []
    scenario_frames = record_frames(scenario_sim, request.steps)
    comparison = compare_simulations(baseline_sim, scenario_sim) if request.compare else None
    roads = graph_to_leaflet_roads(scenario_graph, scenario_sim.peak_road_loads(), max_roads=None)
    run_id = str(uuid4())

    minute = parse_hhmm(request.manual_time)
    stats = asdict(scenario_sim.summary())
    stats["time"] = format_hhmm(minute)
    stats["demand_multiplier"] = profile.demand_multiplier(minute)
    baseline_stats = asdict(baseline_sim.summary()) if request.compare else None
    if baseline_stats is not None:
        baseline_stats["time"] = format_hhmm(minute)
        baseline_stats["demand_multiplier"] = profile.demand_multiplier(minute)

    return {
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
    }


def _run_preview(request: SimulationRequest) -> dict[str, Any]:
    graph = load_preset_graph(request.preset_id, refresh=request.refresh_cache)
    scenario_roads = _apply_scenario_request(graph, request.scenario)
    selected_roads = [road for road in graph.roads.values() if road.is_open and len(graph.road_geometry(road.road_id)) >= 2]
    selected_roads.sort(key=lambda road: road.road_id)
    vehicle_paths = _build_preview_vehicle_paths(graph, selected_roads, request.vehicles, request.seed, request.manual_time)
    run_id = str(uuid4())
    road_counts: dict[str, int] = {road.road_id: 0 for road in selected_roads}
    for path in vehicle_paths:
        road_counts[path["roadId"]] = road_counts.get(path["roadId"], 0) + 1
    road_loads = {
        road.road_id: min(1.5, road_counts.get(road.road_id, 0) / max(road.effective_capacity(), 1))
        for road in selected_roads
    }
    for road_id in scenario_roads:
        road_loads[road_id] = 1.0
    leaflet_roads = graph_to_leaflet_roads(graph, road_loads, max_roads=None)
    _attach_preview_next_roads(graph, leaflet_roads, seed=request.seed)
    profile = load_time_profile()
    minute = parse_hhmm(request.manual_time)
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
    }
    return {
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
    }


def _attach_preview_next_roads(graph: CityGraph, leaflet_roads: list[dict[str, object]], seed: int) -> None:
    import random

    rng = random.Random(seed + 137)
    open_road_ids = {road["id"] for road in leaflet_roads if road.get("isOpen")}
    fallback_roads = sorted(open_road_ids)
    next_by_road: dict[str, str] = {}
    for road_id in fallback_roads:
        road = graph.roads[road_id]
        candidates = [
            candidate_id
            for candidate_id in graph.outgoing.get(road.end_node, [])
            if candidate_id in open_road_ids and graph.roads[candidate_id].is_open
        ]
        if candidates:
            candidates.sort(key=lambda candidate_id: (graph.roads[candidate_id].road_class, graph.roads[candidate_id].length_m))
            next_by_road[road_id] = rng.choice(candidates[: min(len(candidates), 5)])
        else:
            next_by_road[road_id] = rng.choice(fallback_roads) if fallback_roads else road_id

    for road in leaflet_roads:
        road["nextRoadId"] = next_by_road.get(str(road["id"]), road["id"])


def _build_preview_vehicle_paths(graph: CityGraph, roads: list[Any], vehicle_count: int, seed: int, manual_time: str) -> list[dict[str, object]]:
    import random

    rng = random.Random(seed)
    profile = load_time_profile()
    minute = parse_hhmm(manual_time)
    usable_roads = [road for road in roads if road.is_open and len(graph.road_geometry(road.road_id)) >= 2]
    if not usable_roads:
        raise ValueError("No roads available for preview")
    rng.shuffle(usable_roads)
    vehicles: list[dict[str, object]] = []
    for index in range(vehicle_count):
        road = usable_roads[index % len(usable_roads)]
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
            }
        )
    return vehicles


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
    surge_node: str | None = None,
) -> TrafficSimulation:
    sim = TrafficSimulation(
        graph=graph,
        tick_seconds=request.tick_seconds,
        routing_algorithm="astar",
        manual_time=request.manual_time,
        auto_time=request.auto_time,
        time_speed_multiplier=request.time_speed_multiplier,
        time_profile=load_time_profile(),
    )
    vehicles = generate_vehicle_demand(
        graph,
        request.vehicles,
        seed=request.seed,
        horizon_s=horizon_s,
        surge_node=surge_node,
        policy=build_policy(request.policy),
        minute_of_day=parse_hhmm(request.manual_time),
    )
    for vehicle in vehicles:
        sim.add_vehicle(vehicle)
    return sim


def _apply_scenario_request(graph: CityGraph, scenario: ScenarioRequest) -> list[str]:
    if scenario.type == "none":
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


def _pick_representative_road(graph: CityGraph) -> str:
    return max(graph.roads, key=lambda road_id: graph.roads[road_id].length_m)


def _scenario_node(graph: CityGraph, road_id: str) -> str | None:
    if road_id not in graph.roads:
        return None
    return graph.roads[road_id].start_node


def _road_payload(graph: CityGraph, road_id: str) -> dict[str, object]:
    road = graph.roads[road_id]
    return {
        "id": road_id,
        "name": road.metadata.get("name") or road_id,
        "startNode": road.start_node,
        "endNode": road.end_node,
        "lengthM": road.length_m,
        "capacity": road.capacity,
        "effectiveCapacity": road.effective_capacity(),
        "maxSpeedKph": road.max_speed_kph,
        "lanes": road.lanes,
        "roadClass": road.road_class,
        "signalDelayS": road.signal_delay_s,
        "isOpen": road.is_open,
        "geometry": graph.road_geometry(road_id),
        "metadata": road.metadata,
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
        "procedural": run.get("procedural", False),
        "frameCount": len(run["frames"]),
        "roadCount": len(run["roads"]),
    }


def _get_run(run_id: str) -> dict[str, Any]:
    if run_id not in RUNS:
        raise HTTPException(status_code=404, detail=f"Unknown simulation id: {run_id}")
    return RUNS[run_id]
