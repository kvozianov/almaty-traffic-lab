from __future__ import annotations

import argparse
import random

from .network import build_demo_city_graph, load_graph_from_osm_bbox, load_graph_from_osm_place
from .scenarios import add_bypass_road, apply_accident, close_road_for_repair, retime_traffic_signal
from .simulation import TrafficSimulation


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the traffic simulation MVP")
    parser.add_argument(
        "--source",
        choices=["demo", "place", "bbox"],
        default="demo",
        help="Road network source",
    )
    parser.add_argument(
        "--place",
        default="Almaly District, Almaty, Kazakhstan",
        help="OSM place name to load when --source place is used",
    )
    parser.add_argument(
        "--bbox",
        type=float,
        nargs=4,
        metavar=("NORTH", "SOUTH", "EAST", "WEST"),
        help="Bounding box to load from OSM when --source bbox is used",
    )
    parser.add_argument(
        "--network-type",
        default="drive",
        help="OSMnx network type, for example drive or drive_service",
    )
    parser.add_argument("--vehicles", type=int, default=25, help="Number of vehicles to spawn")
    parser.add_argument("--steps", type=int, default=120, help="Number of simulation ticks")
    parser.add_argument("--tick-seconds", type=int, default=10, help="Length of one simulation tick")
    parser.add_argument(
        "--scenario",
        choices=["none", "accident", "repair", "signal", "new-road"],
        default="none",
        help="Scenario to apply before the run",
    )
    parser.add_argument("--seed", type=int, default=7, help="Random seed")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    rng = random.Random(args.seed)

    try:
        graph = _load_graph(args)
    except Exception as exc:
        raise SystemExit(_format_graph_loading_error(args, exc)) from exc
    _apply_scenario(graph, args.scenario)
    sim = TrafficSimulation(graph=graph, tick_seconds=args.tick_seconds, routing_algorithm="astar")

    nodes = list(graph.nodes)
    spawned = _spawn_random_vehicles(sim, nodes, args.vehicles, rng)

    stats = sim.step(args.steps)

    print(f"Source: {args.source}")
    if args.source == "place":
        print(f"Place: {args.place}")
    elif args.source == "bbox" and args.bbox:
        north, south, east, west = args.bbox
        print(f"BBox: north={north}, south={south}, east={east}, west={west}")
    print(f"Scenario: {args.scenario}")
    print(f"Ticks: {stats.tick}")
    print(f"Simulation time: {stats.sim_time_s / 60:.1f} min")
    print(f"Road nodes: {len(graph.nodes)}")
    print(f"Road edges: {len(graph.roads)}")
    print(f"Arrived vehicles: {stats.arrived_vehicles}/{spawned}")
    print(f"Stuck vehicles: {stats.stuck_vehicles}")
    print(f"Average trip time: {stats.average_trip_time_s / 60:.2f} min")
    print(f"Average road load: {stats.average_road_load:.2f}")
    print(f"Max road load: {stats.max_road_load:.2f}")

    busiest = sorted(sim.peak_road_loads().items(), key=lambda item: item[1], reverse=True)[:5]
    print("Top congested roads:")
    for road_id, load in busiest:
        print(f"  {road_id}: {load:.2f}")


def _load_graph(args: argparse.Namespace):
    if args.source == "demo":
        return build_demo_city_graph()
    if args.source == "place":
        return load_graph_from_osm_place(args.place, network_type=args.network_type)
    if not args.bbox:
        raise SystemExit("--bbox NORTH SOUTH EAST WEST is required when --source bbox is used")
    north, south, east, west = args.bbox
    return load_graph_from_osm_bbox(north, south, east, west, network_type=args.network_type)


def _format_graph_loading_error(args: argparse.Namespace, exc: Exception) -> str:
    details = str(exc).strip() or exc.__class__.__name__
    if args.source == "demo":
        return f"Failed to load demo graph: {details}"
    return (
        "Failed to load the OpenStreetMap road graph.\n"
        f"Reason: {details}\n"
        "Try a smaller bbox or a smaller district first. "
        "A verified example is: --source bbox --bbox 43.245 43.240 76.950 76.940"
    )


def _spawn_random_vehicles(sim: TrafficSimulation, nodes: list[str], vehicle_count: int, rng: random.Random) -> int:
    spawned = 0
    attempts = 0
    max_attempts = max(vehicle_count * 12, 50)

    while spawned < vehicle_count and attempts < max_attempts:
        attempts += 1
        start = rng.choice(nodes)
        destination = rng.choice([node for node in nodes if node != start])
        try:
            sim.spawn_vehicle(f"car-{spawned + 1}", start, destination)
        except ValueError:
            continue
        spawned += 1

    if spawned == 0:
        raise SystemExit("Could not generate any valid routes for the selected graph")
    return spawned


def _apply_scenario(graph, scenario: str) -> None:
    road_id = _pick_scenario_road(graph)
    if scenario == "accident":
        apply_accident(graph, road_id)
    elif scenario == "repair":
        close_road_for_repair(graph, road_id)
    elif scenario == "signal":
        retime_traffic_signal(graph, road_id, new_delay_s=60)
    elif scenario == "new-road":
        start_node = _pick_node(graph, preferred="west")
        end_node = _pick_node(graph, preferred="east", exclude={start_node})
        add_bypass_road(
            graph,
            road_id="express_connector",
            start_node=start_node,
            end_node=end_node,
            length_m=1400,
            max_speed_kph=60,
            capacity=24,
            signal_delay_s=4,
        )


def _pick_scenario_road(graph) -> str:
    preferred_ids = ["abay_ab", "seifullin_ab", "satpayev_ab"]
    for road_id in preferred_ids:
        if road_id in graph.roads:
            return road_id
    return max(graph.roads, key=lambda current_id: graph.roads[current_id].length_m)


def _pick_node(graph, preferred: str, exclude: set[str] | None = None) -> str:
    if preferred in graph.nodes and preferred not in (exclude or set()):
        return preferred
    exclude = exclude or set()
    for node_id in graph.nodes:
        if node_id not in exclude:
            return node_id
    raise SystemExit("No available nodes for scenario road creation")


if __name__ == "__main__":
    main()
