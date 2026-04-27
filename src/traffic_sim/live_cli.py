from __future__ import annotations

import random
import tkinter as tk
from tkinter import ttk

from .cli import _apply_scenario, _format_graph_loading_error, _load_graph, _spawn_random_vehicles, build_parser
from .simulation import TrafficSimulation
from .visualization import _bounds, _project_point, _vehicle_position


CANVAS_WIDTH = 1000
CANVAS_HEIGHT = 700


class LiveTrafficApp:
    def __init__(self, root: tk.Tk, sim: TrafficSimulation, max_steps: int, fps: int) -> None:
        self.root = root
        self.sim = sim
        self.max_steps = max_steps
        self.frame_delay_ms = max(20, int(1000 / max(fps, 1)))
        self.running = True
        self.road_items: dict[str, int] = {}
        self.vehicle_items: dict[str, int] = {}
        self.bounds = _bounds([point for road_id in sim.graph.roads for point in sim.graph.road_geometry(road_id)])

        root.title("Traffic Simulation Live")
        root.geometry("1240x780")
        root.configure(bg="#f5f3ec")

        self.canvas = tk.Canvas(root, width=CANVAS_WIDTH, height=CANVAS_HEIGHT, bg="#fbfaf6", highlightthickness=0)
        self.canvas.grid(row=0, column=0, rowspan=2, sticky="nsew", padx=14, pady=14)

        panel = ttk.Frame(root, padding=14)
        panel.grid(row=0, column=1, sticky="nsew", padx=(0, 14), pady=14)

        ttk.Label(panel, text="Traffic Simulation Live", font=("Avenir Next", 18, "bold")).grid(row=0, column=0, sticky="w")
        self.status_label = ttk.Label(panel, text="")
        self.status_label.grid(row=1, column=0, sticky="w", pady=(14, 0))
        self.vehicle_label = ttk.Label(panel, text="")
        self.vehicle_label.grid(row=2, column=0, sticky="w", pady=(8, 0))
        self.trip_label = ttk.Label(panel, text="")
        self.trip_label.grid(row=3, column=0, sticky="w", pady=(8, 0))
        self.load_label = ttk.Label(panel, text="")
        self.load_label.grid(row=4, column=0, sticky="w", pady=(8, 0))

        self.toggle_button = ttk.Button(panel, text="Pause", command=self.toggle)
        self.toggle_button.grid(row=5, column=0, sticky="ew", pady=(20, 0))
        ttk.Label(panel, text="Space: pause/resume").grid(row=6, column=0, sticky="w", pady=(12, 0))

        root.grid_columnconfigure(0, weight=1)
        root.grid_rowconfigure(0, weight=1)
        root.bind("<space>", lambda _event: self.toggle())

        self._draw_roads()
        self._render()
        self.root.after(self.frame_delay_ms, self._tick)

    def toggle(self) -> None:
        self.running = not self.running
        self.toggle_button.configure(text="Pause" if self.running else "Start")

    def _tick(self) -> None:
        if self.running and self.sim.tick < self.max_steps:
            self.sim.step()
            self._render()
        self.root.after(self.frame_delay_ms, self._tick)

    def _draw_roads(self) -> None:
        for road_id in self.sim.graph.roads:
            points = [self._project(point) for point in self.sim.graph.road_geometry(road_id)]
            flat_points = [coord for point in points for coord in point]
            item = self.canvas.create_line(
                *flat_points,
                fill="#74828f",
                width=3,
                capstyle=tk.ROUND,
                joinstyle=tk.ROUND,
            )
            self.road_items[road_id] = item

    def _render(self) -> None:
        self._render_roads()
        self._render_vehicles()
        self._render_stats()

    def _render_roads(self) -> None:
        loads = self.sim.road_loads()
        for road_id, item in self.road_items.items():
            road = self.sim.graph.roads[road_id]
            load = loads.get(road_id, 0.0)
            color = self._road_color(load, road.is_open)
            width = 2.5 + min(load, 1.5) * 6
            self.canvas.itemconfigure(item, fill=color, width=width)

    def _render_vehicles(self) -> None:
        active_ids = set()
        for vehicle in self.sim.vehicles.values():
            if vehicle.state != "moving" or vehicle.current_road_id is None:
                continue
            active_ids.add(vehicle.vehicle_id)
            x, y = _vehicle_position(self.sim.graph, vehicle.current_road_id, vehicle.progress_m)
            px, py = self._project((x, y))
            item = self.vehicle_items.get(vehicle.vehicle_id)
            if item is None:
                item = self.canvas.create_oval(px - 6, py - 6, px + 6, py + 6, fill="#0969da", outline="#ffffff", width=2)
                self.vehicle_items[vehicle.vehicle_id] = item
            else:
                self.canvas.coords(item, px - 6, py - 6, px + 6, py + 6)

        for vehicle_id, item in list(self.vehicle_items.items()):
            if vehicle_id not in active_ids:
                self.canvas.delete(item)
                del self.vehicle_items[vehicle_id]

    def _render_stats(self) -> None:
        stats = self.sim.summary()
        self.status_label.configure(text=f"Tick: {stats.tick}/{self.max_steps}   Time: {stats.sim_time_s / 60:.1f} min")
        self.vehicle_label.configure(
            text=f"Moving: {stats.active_vehicles}   Arrived: {stats.arrived_vehicles}   Stuck: {stats.stuck_vehicles}"
        )
        self.trip_label.configure(text=f"Average trip: {stats.average_trip_time_s / 60:.2f} min")
        self.load_label.configure(text=f"Max road load: {stats.max_road_load:.2f}   Avg load: {stats.average_road_load:.2f}")

    def _project(self, point: tuple[float, float]) -> tuple[float, float]:
        return _project_point(point, self.bounds)

    @staticmethod
    def _road_color(load: float, is_open: bool) -> str:
        if not is_open:
            return "#222222"
        if load >= 0.65:
            return "#d64737"
        if load >= 0.25:
            return "#df9c28"
        return "#74828f"


def main() -> None:
    parser = build_parser()
    parser.description = "Run a real-time traffic simulation window"
    parser.add_argument("--fps", type=int, default=12, help="Render frames per second")
    args = parser.parse_args()
    rng = random.Random(args.seed)

    try:
        graph = _load_graph(args)
    except Exception as exc:
        raise SystemExit(_format_graph_loading_error(args, exc)) from exc

    _apply_scenario(graph, args.scenario)
    sim = TrafficSimulation(graph=graph, tick_seconds=args.tick_seconds, routing_algorithm="astar")
    _spawn_random_vehicles(sim, list(graph.nodes), args.vehicles, rng)

    root = tk.Tk()
    LiveTrafficApp(root, sim=sim, max_steps=args.steps, fps=args.fps)
    root.mainloop()


if __name__ == "__main__":
    main()
