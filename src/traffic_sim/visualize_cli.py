from __future__ import annotations

from pathlib import Path
import random

from .cli import _apply_scenario, _format_graph_loading_error, _load_graph, _spawn_random_vehicles, build_parser
from .simulation import TrafficSimulation
from .visualization import record_frames, write_visualization_html


def main() -> None:
    parser = build_parser()
    parser.description = "Generate an animated HTML traffic map"
    parser.add_argument(
        "--output",
        default="reports/traffic_simulation.html",
        help="Output HTML path",
    )
    args = parser.parse_args()
    rng = random.Random(args.seed)

    try:
        graph = _load_graph(args)
    except Exception as exc:
        raise SystemExit(_format_graph_loading_error(args, exc)) from exc

    _apply_scenario(graph, args.scenario)
    sim = TrafficSimulation(graph=graph, tick_seconds=args.tick_seconds, routing_algorithm="astar")
    spawned = _spawn_random_vehicles(sim, list(graph.nodes), args.vehicles, rng)
    frames = record_frames(sim, args.steps)
    title = f"Traffic Simulation: {args.source} / {args.scenario}"
    output = write_visualization_html(Path(args.output), graph, sim, frames, title=title)

    stats = sim.summary()
    print(f"Visualization: {output.resolve()}")
    print(f"Road nodes: {len(graph.nodes)}")
    print(f"Road edges: {len(graph.roads)}")
    print(f"Vehicles spawned: {spawned}")
    print(f"Arrived vehicles: {stats.arrived_vehicles}/{spawned}")
    print(f"Average trip time: {stats.average_trip_time_s / 60:.2f} min")
    print(f"Max road load: {stats.max_road_load:.2f}")


if __name__ == "__main__":
    main()
