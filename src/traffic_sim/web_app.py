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

from .analytics import (
    compare_simulations,
    export_metrics_json,
    export_road_loads_csv,
    graph_to_leaflet_roads,
    simulation_frames_to_leaflet,
    top_loaded_roads,
)
from .demand import generate_vehicle_demand
from .graph_cache import list_presets, load_preset_graph
from .network import CityGraph
from .scenarios import add_bypass_road, apply_accident, close_road_for_repair, retime_traffic_signal
from .simulation import TrafficSimulation
from .visualization import record_frames


STATIC_DIR = Path(__file__).parent / "web" / "static"
RUNS: dict[str, dict[str, Any]] = {}


class ScenarioRequest(BaseModel):
    type: str = Field(default="none")
    road_id: str | None = None
    capacity_factor: float = 0.3
    speed_factor: float = 0.45
    signal_delay_s: float = 60.0
    demand_surge: bool = False


class SimulationRequest(BaseModel):
    preset_id: str = "full_almaty"
    vehicles: int = Field(default=80, ge=1, le=1500)
    steps: int = Field(default=240, ge=1, le=3000)
    tick_seconds: int = Field(default=10, ge=1, le=120)
    seed: int = 7
    refresh_cache: bool = False
    compare: bool = True
    scenario: ScenarioRequest = Field(default_factory=ScenarioRequest)


def create_app() -> FastAPI:
    app = FastAPI(title="Almaty Traffic Simulation Dashboard")
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    @app.get("/api/presets")
    def presets() -> dict[str, object]:
        return {"presets": list_presets()}

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

    horizon_s = request.steps * request.tick_seconds * 0.65
    surge_node = _scenario_node(scenario_graph, scenario_roads[0]) if request.scenario.demand_surge and scenario_roads else None
    baseline_sim = _build_simulation(baseline_graph, request, horizon_s=horizon_s)
    scenario_sim = _build_simulation(scenario_graph, request, horizon_s=horizon_s, surge_node=surge_node)

    baseline_frames = record_frames(baseline_sim, request.steps) if request.compare else []
    scenario_frames = record_frames(scenario_sim, request.steps)
    comparison = compare_simulations(baseline_sim, scenario_sim) if request.compare else None
    road_limit = 6000 if request.preset_id in {"full_almaty", "full_almaty_fast"} else None
    roads = graph_to_leaflet_roads(scenario_graph, scenario_sim.peak_road_loads(), max_roads=road_limit)
    run_id = str(uuid4())

    return {
        "id": run_id,
        "request": request.model_dump(),
        "presetId": request.preset_id,
        "roads": roads,
        "scenario_roads": scenario_roads,
        "frames": simulation_frames_to_leaflet(scenario_sim, scenario_frames),
        "baseline_frames": simulation_frames_to_leaflet(baseline_sim, baseline_frames) if baseline_frames else None,
        "stats": asdict(scenario_sim.summary()),
        "baseline_stats": asdict(baseline_sim.summary()) if request.compare else None,
        "comparison": comparison,
        "hot_roads": top_loaded_roads(scenario_sim),
        "scenario_sim": scenario_sim,
    }


def _run_preview(request: SimulationRequest) -> dict[str, Any]:
    graph = load_preset_graph(request.preset_id, refresh=request.refresh_cache)
    roads = sorted(graph.roads.values(), key=lambda road: (road.length_m, road.capacity), reverse=True)
    selected_roads = roads[: min(len(roads), 6000)]
    frames = _build_preview_frames(graph, selected_roads, request.vehicles, request.steps, request.seed)
    run_id = str(uuid4())
    road_loads = {road.road_id: min(1.0, (index % 9) / 10) for index, road in enumerate(selected_roads)}
    leaflet_roads = graph_to_leaflet_roads(graph, road_loads, max_roads=6000)
    stats = {
        "tick": request.steps,
        "sim_time_s": request.steps * request.tick_seconds,
        "active_vehicles": request.vehicles,
        "arrived_vehicles": 0,
        "stuck_vehicles": 0,
        "average_trip_time_s": 0.0,
        "max_road_load": max(road_loads.values(), default=0.0),
        "average_road_load": sum(road_loads.values()) / len(road_loads) if road_loads else 0.0,
    }
    return {
        "id": run_id,
        "request": request.model_dump(),
        "presetId": request.preset_id,
        "roads": leaflet_roads,
        "scenario_roads": [],
        "frames": frames,
        "baseline_frames": None,
        "stats": stats,
        "baseline_stats": None,
        "comparison": None,
        "hot_roads": [{"roadId": road.road_id, "load": road_loads.get(road.road_id, 0.0)} for road in selected_roads[:8]],
        "scenario_sim": None,
    }


def _build_preview_frames(graph: CityGraph, roads: list[Any], vehicle_count: int, steps: int, seed: int) -> list[dict[str, object]]:
    import random

    rng = random.Random(seed)
    usable_roads = [road for road in roads if len(graph.road_geometry(road.road_id)) >= 2]
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
    sim = TrafficSimulation(graph=graph, tick_seconds=request.tick_seconds, routing_algorithm="astar")
    vehicles = generate_vehicle_demand(
        graph,
        request.vehicles,
        seed=request.seed,
        horizon_s=horizon_s,
        surge_node=surge_node,
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
    elif scenario.type == "signal":
        retime_traffic_signal(graph, road_id, new_delay_s=scenario.signal_delay_s)
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
        "frameCount": len(run["frames"]),
        "roadCount": len(run["roads"]),
    }


def _get_run(run_id: str) -> dict[str, Any]:
    if run_id not in RUNS:
        raise HTTPException(status_code=404, detail=f"Unknown simulation id: {run_id}")
    return RUNS[run_id]
