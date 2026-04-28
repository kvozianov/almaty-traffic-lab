from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
import csv
import html
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
                "capacity": road.capacity,
                "effectiveCapacity": road.effective_capacity(),
                "maxSpeedKph": road.max_speed_kph,
                "speedModifier": road.speed_modifier,
                "capacityModifier": road.capacity_modifier,
                "speedSource": road.metadata.get("speed_source", "maxspeed_fallback"),
                "lanes": road.lanes,
                "lanesSource": road.metadata.get("lanes_source", "lanes_fallback"),
                "signalCount": road.metadata.get("signal_count", 0),
                "signalDelayS": road.signal_delay_s,
                "timelineEvents": road.metadata.get("timeline_events", []),
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


def build_run_analytics(run: dict[str, object]) -> dict[str, object]:
    roads = list(run.get("roads", []))
    frames = list(run.get("frames", []))
    procedural_vehicles = list(run.get("procedural_vehicles", []))
    stats = dict(run.get("stats", {}))
    request = dict(run.get("request", {}))
    road_loads = [(str(road.get("id")), float(road.get("load", 0.0)), str(road.get("name") or road.get("id"))) for road in roads]
    top_roads = [
        {"roadId": road_id, "name": name, "load": round(load, 4)}
        for road_id, load, name in sorted(road_loads, key=lambda item: item[1], reverse=True)[:10]
    ]

    if procedural_vehicles:
        average_speed = _average([float(vehicle.get("speedKph", 0.0)) for vehicle in procedural_vehicles])
        congestion_over_time = _synthetic_series(float(stats.get("average_road_load", 0.0)), int(request.get("steps", 240)), wave=0.18)
        average_speed_over_time = _synthetic_series(average_speed, int(request.get("steps", 240)), wave=0.12, floor=3.0)
    else:
        congestion_over_time = [
            {"tick": int(frame.get("tick", index)), "value": min(1.5, len(frame.get("vehicles", [])) / max(int(request.get("vehicles", 1)), 1))}
            for index, frame in enumerate(frames[:: max(1, len(frames) // 80)])
        ]
        average_speed_over_time = _synthetic_series(float(stats.get("average_trip_time_s", 0.0)) / 60 or 22.0, len(frames), wave=0.1, floor=1.0)

    comparison = run.get("comparison")
    return {
        "runId": run.get("id"),
        "congestionOverTime": congestion_over_time,
        "averageSpeedOverTime": average_speed_over_time,
        "topRoads": top_roads,
        "corridorStats": corridor_stats_from_roads(roads),
        "odPairs": od_pairs_from_vehicles(procedural_vehicles),
        "routeCoverage": route_coverage_from_vehicles(procedural_vehicles, roads),
        "beforeAfter": comparison.get("delta") if isinstance(comparison, dict) else None,
        "heatmap": heatmap_points_from_roads(roads, limit=350),
        "events": run.get("events", []),
        "zones": run.get("zones", []),
    }


def corridor_stats_from_roads(roads: list[object], corridor_path: str | Path = "data/corridors/almaty_major_roads.json") -> list[dict[str, object]]:
    try:
        corridors = json.loads(Path(corridor_path).read_text(encoding="utf-8")).get("corridors", [])
    except FileNotFoundError:
        corridors = []
    result: list[dict[str, object]] = []
    for corridor in corridors:
        aliases = [str(corridor.get("id", "")), str(corridor.get("name", "")), *[str(alias) for alias in corridor.get("aliases", [])]]
        matched = [
            road
            for road in roads
            if any(alias and alias.lower() in str(road.get("name") or road.get("id", "")).lower() for alias in aliases)
        ]
        loads = [float(road.get("load", 0.0)) for road in matched]
        speeds = [float(road.get("maxSpeedKph", 0.0)) * float(road.get("speedModifier", 1.0)) for road in matched]
        result.append(
            {
                "id": corridor.get("id"),
                "name": corridor.get("name"),
                "roadCount": len(matched),
                "averageLoad": round(_average(loads), 4),
                "maxLoad": round(max(loads, default=0.0), 4),
                "estimatedSpeedKph": round(_average(speeds), 1),
            }
        )
    return result


def heatmap_points_from_roads(roads: list[object], limit: int = 350) -> list[dict[str, object]]:
    points: list[dict[str, object]] = []
    for road in sorted(roads, key=lambda item: float(item.get("load", 0.0)), reverse=True)[:limit]:
        coords = road.get("coords")
        if not isinstance(coords, list) or not coords:
            continue
        mid = coords[len(coords) // 2]
        if not isinstance(mid, list) or len(mid) < 2:
            continue
        points.append({"lat": mid[0], "lng": mid[1], "weight": min(1.0, max(0.05, float(road.get("load", 0.0))))})
    return points


def od_pairs_from_vehicles(vehicles: list[object], limit: int = 10) -> list[dict[str, object]]:
    counts: dict[tuple[str, str], int] = {}
    for vehicle in vehicles:
        origin = vehicle.get("originZone") if isinstance(vehicle, dict) else None
        destination = vehicle.get("destinationZone") if isinstance(vehicle, dict) else None
        if not origin or not destination:
            continue
        key = (str(origin), str(destination))
        counts[key] = counts.get(key, 0) + 1
    return [
        {"origin": origin, "destination": destination, "vehicles": count}
        for (origin, destination), count in sorted(counts.items(), key=lambda item: item[1], reverse=True)[:limit]
    ]


def route_coverage_from_vehicles(vehicles: list[object], roads: list[object]) -> dict[str, object]:
    covered_roads: set[str] = set()
    routed_vehicles = 0
    total_route_length = 0
    for vehicle in vehicles:
        route_ids = vehicle.get("routeRoadIds") if isinstance(vehicle, dict) else None
        if not isinstance(route_ids, list):
            continue
        if len(route_ids) > 1:
            routed_vehicles += 1
            total_route_length += len(route_ids)
        covered_roads.update(str(road_id) for road_id in route_ids)
    total_roads = max(1, len(roads))
    return {
        "coveredRoads": len(covered_roads),
        "totalRoads": len(roads),
        "coverageRatio": round(len(covered_roads) / total_roads, 4),
        "routedVehicles": routed_vehicles,
        "averageRouteRoads": round(total_route_length / routed_vehicles, 2) if routed_vehicles else 0.0,
    }


def export_research_report_html(path: str | Path, run: dict[str, object], analytics: dict[str, object]) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    stats = dict(run.get("stats", {}))
    request = dict(run.get("request", {}))
    top_rows = "\n".join(
        f"<tr><td>{html.escape(str(item.get('name') or item.get('roadId')))}</td><td>{float(item.get('load', 0.0)):.2f}</td></tr>"
        for item in analytics.get("topRoads", [])
    )
    corridor_rows = "\n".join(
        f"<tr><td>{html.escape(str(item.get('name')))}</td><td>{item.get('roadCount')}</td><td>{float(item.get('averageLoad', 0.0)):.2f}</td><td>{float(item.get('estimatedSpeedKph', 0.0)):.1f}</td></tr>"
        for item in analytics.get("corridorStats", [])
    )
    od_rows = "\n".join(
        f"<tr><td>{html.escape(str(item.get('origin')))}</td><td>{html.escape(str(item.get('destination')))}</td><td>{item.get('vehicles')}</td></tr>"
        for item in analytics.get("odPairs", [])
    )
    coverage = dict(analytics.get("routeCoverage", {}))
    embedded = html.escape(json.dumps({"request": request, "stats": stats, "analytics": analytics}, ensure_ascii=True, indent=2))
    output.write_text(
        f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Almaty Traffic Research Report</title>
  <style>
    body {{ font-family: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; margin: 32px; color: #1f2729; }}
    h1 {{ margin-bottom: 4px; }}
    .grid {{ display: grid; grid-template-columns: repeat(4, minmax(120px, 1fr)); gap: 12px; margin: 24px 0; }}
    .card {{ border: 1px solid #d8d1c4; border-radius: 8px; padding: 14px; }}
    .card span {{ display: block; color: #65706f; font-size: 12px; font-weight: 700; text-transform: uppercase; }}
    .card strong {{ display: block; margin-top: 8px; font-size: 24px; }}
    table {{ border-collapse: collapse; width: 100%; margin: 16px 0 28px; }}
    th, td {{ border-bottom: 1px solid #e4ded2; padding: 9px; text-align: left; }}
    pre {{ background: #f5f1e8; padding: 16px; border-radius: 8px; overflow: auto; }}
  </style>
</head>
<body>
  <h1>Almaty Traffic Research Report</h1>
  <p>Run {html.escape(str(run.get("id")))} | preset {html.escape(str(run.get("presetId")))} | time {html.escape(str(stats.get("time", request.get("manual_time", "17:00"))))}</p>
  <section class="grid">
    <div class="card"><span>Vehicles</span><strong>{html.escape(str(request.get("vehicles")))}</strong></div>
    <div class="card"><span>Max load</span><strong>{float(stats.get("max_road_load", 0.0)):.2f}</strong></div>
    <div class="card"><span>Avg trip</span><strong>{float(stats.get("average_trip_time_s", 0.0)) / 60:.2f} min</strong></div>
    <div class="card"><span>Reroutes</span><strong>{html.escape(str(stats.get("reroutes", 0)))}</strong></div>
    <div class="card"><span>Route coverage</span><strong>{float(coverage.get("coverageRatio", 0.0)) * 100:.1f}%</strong></div>
  </section>
  <h2>Top Loaded Roads</h2>
  <table><thead><tr><th>Road</th><th>Load</th></tr></thead><tbody>{top_rows}</tbody></table>
  <h2>Corridor Stats</h2>
  <table><thead><tr><th>Corridor</th><th>Roads</th><th>Average load</th><th>Estimated speed</th></tr></thead><tbody>{corridor_rows}</tbody></table>
  <h2>Top OD Flows</h2>
  <table><thead><tr><th>Origin</th><th>Destination</th><th>Vehicles</th></tr></thead><tbody>{od_rows}</tbody></table>
  <h2>Embedded Summary JSON</h2>
  <pre>{embedded}</pre>
</body>
</html>""",
        encoding="utf-8",
    )
    return output


def export_metrics_json(path: str | Path, payload: dict[str, object]) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")
    return output


def _synthetic_series(base: float, steps: int, wave: float = 0.15, floor: float = 0.0) -> list[dict[str, object]]:
    count = min(80, max(12, steps // 4 if steps else 12))
    if count <= 1:
        return [{"tick": 0, "value": round(max(floor, base), 4)}]
    values = []
    for index in range(count):
        ratio = index / (count - 1)
        factor = 1 + wave * (0.5 - abs(ratio - 0.5)) * 2
        values.append({"tick": int(ratio * max(steps, 1)), "value": round(max(floor, base * factor), 4)})
    return values


def _average(values: list[float]) -> float:
    clean = [value for value in values if value >= 0]
    return sum(clean) / len(clean) if clean else 0.0


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
