from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
import csv
import json

from .network import CityGraph
from .simulation import TrafficSimulation
from .visualization import SimulationFrame, _vehicle_position


def graph_to_leaflet_roads(
    graph: CityGraph,
    loads: dict[str, float] | None = None,
    max_roads: int | None = None,
) -> list[dict[str, object]]:
    loads = loads or {}
    road_items = list(graph.roads.items())
    if max_roads is not None and len(road_items) > max_roads:
        road_items = sorted(
            road_items,
            key=lambda item: (loads.get(item[0], 0.0), item[1].length_m, item[1].capacity),
            reverse=True,
        )[:max_roads]

    roads: list[dict[str, object]] = []
    for road_id, road in road_items:
        coords = [[point[1], point[0]] for point in graph.road_geometry(road_id)]
        roads.append(
            {
                "id": road_id,
                "name": road.metadata.get("name") or road_id,
                "coords": coords,
                "load": loads.get(road_id, 0.0),
                "isOpen": road.is_open,
                "scenario": road.metadata.get("scenario"),
            }
        )
    return roads


def simulation_frames_to_leaflet(sim: TrafficSimulation, frames: list[SimulationFrame]) -> list[dict[str, object]]:
    payload: list[dict[str, object]] = []
    for frame in frames:
        vehicles = []
        for raw_vehicle in frame.vehicles:
            vehicles.append(
                {
                    "id": raw_vehicle.vehicle_id,
                    "lat": raw_vehicle.y,
                    "lng": raw_vehicle.x,
                    "state": raw_vehicle.state,
                }
            )
        payload.append({"tick": frame.tick, "simTimeS": frame.sim_time_s, "vehicles": vehicles})
    return payload


def live_frame_to_leaflet(sim: TrafficSimulation) -> dict[str, object]:
    vehicles = []
    for vehicle in sim.vehicles.values():
        if vehicle.state not in {"moving", "queued"} or vehicle.current_road_id is None:
            continue
        x, y = _vehicle_position(sim.graph, vehicle.current_road_id, vehicle.progress_m)
        vehicles.append({"id": vehicle.vehicle_id, "lat": y, "lng": x, "state": vehicle.state})
    return {
        "tick": sim.tick,
        "simTimeS": sim.sim_time_s,
        "vehicles": vehicles,
        "stats": asdict(sim.summary()),
        "roadLoads": sim.road_loads(),
    }


def compare_simulations(baseline: TrafficSimulation, scenario: TrafficSimulation) -> dict[str, object]:
    baseline_stats = asdict(baseline.summary())
    scenario_stats = asdict(scenario.summary())
    return {
        "baseline": baseline_stats,
        "scenario": scenario_stats,
        "delta": {
            "averageTripTimeS": scenario_stats["average_trip_time_s"] - baseline_stats["average_trip_time_s"],
            "arrivedVehicles": scenario_stats["arrived_vehicles"] - baseline_stats["arrived_vehicles"],
            "stuckVehicles": scenario_stats["stuck_vehicles"] - baseline_stats["stuck_vehicles"],
            "maxRoadLoad": scenario_stats["max_road_load"] - baseline_stats["max_road_load"],
        },
        "hotRoads": top_loaded_roads(scenario, limit=8),
    }


def top_loaded_roads(sim: TrafficSimulation, limit: int = 8) -> list[dict[str, object]]:
    return [
        {"roadId": road_id, "load": load}
        for road_id, load in sorted(sim.peak_road_loads().items(), key=lambda item: item[1], reverse=True)[:limit]
    ]


def export_metrics_json(path: str | Path, payload: dict[str, object]) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")
    return output


def export_road_loads_csv(path: str | Path, sim: TrafficSimulation) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=["road_id", "peak_load", "current_load"])
        writer.writeheader()
        current_loads = sim.road_loads()
        for road_id, peak_load in sim.peak_road_loads().items():
            writer.writerow({"road_id": road_id, "peak_load": peak_load, "current_load": current_loads.get(road_id, 0.0)})
    return output
