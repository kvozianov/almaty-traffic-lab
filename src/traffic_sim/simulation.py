from __future__ import annotations

from dataclasses import replace

from .models import SimulationStats, Vehicle
from .network import CityGraph
from .time_profiles import TimeProfile, load_time_profile, parse_hhmm


class TrafficSimulation:
    def __init__(
        self,
        graph: CityGraph,
        tick_seconds: int = 10,
        routing_algorithm: str = "dijkstra",
        reroute_on_change: bool = True,
        manual_time: str = "12:00",
        auto_time: bool = False,
        time_speed_multiplier: float = 1.0,
        time_profile: TimeProfile | None = None,
        reroute_interval_ticks: int = 0,
    ) -> None:
        self.graph = graph
        self.tick_seconds = tick_seconds
        self.routing_algorithm = routing_algorithm
        self.reroute_on_change = reroute_on_change
        self.minute_of_day = parse_hhmm(manual_time)
        self.auto_time = auto_time
        self.time_speed_multiplier = time_speed_multiplier
        self.time_profile = time_profile or load_time_profile()
        self.reroute_interval_ticks = max(0, int(reroute_interval_ticks))
        self.tick = 0
        self.sim_time_s = 0.0
        self.vehicles: dict[str, Vehicle] = {}
        self.road_occupancy: dict[str, set[str]] = {road_id: set() for road_id in graph.roads}
        self.road_peak_loads: dict[str, float] = {road_id: 0.0 for road_id in graph.roads}
        self.network_load_samples: list[float] = []
        self.history: list[SimulationStats] = []

    def spawn_vehicle(self, vehicle_id: str, start_node: str, destination_node: str) -> Vehicle:
        vehicle = Vehicle(vehicle_id=vehicle_id, start_node=start_node, destination_node=destination_node)
        self.add_vehicle(vehicle)
        return vehicle

    def add_vehicle(self, vehicle: Vehicle) -> None:
        vehicle = replace(vehicle)
        self._assign_route(vehicle, vehicle.start_node, count_as_reroute=False)
        if vehicle.spawn_road_id in self.graph.roads and vehicle.route_roads:
            spawn_road = self.graph.roads[vehicle.spawn_road_id]
            if spawn_road.end_node == vehicle.start_node and spawn_road.is_open:
                vehicle.route_nodes = [spawn_road.start_node, *vehicle.route_nodes]
                vehicle.route_roads = [spawn_road.road_id, *vehicle.route_roads]
                vehicle.current_road_index = 0
                vehicle.progress_m = max(0.0, min(vehicle.spawn_ratio, 0.98)) * spawn_road.length_m
                vehicle.state = "moving"
        if vehicle.departure_time_s > self.sim_time_s and vehicle.route_roads:
            vehicle.state = "pending"
        self.vehicles[vehicle.vehicle_id] = vehicle
        if vehicle.state == "moving" and vehicle.current_road_id is not None:
            self.road_occupancy.setdefault(vehicle.current_road_id, set()).add(vehicle.vehicle_id)

    def step(self, steps: int = 1) -> SimulationStats:
        for _ in range(steps):
            self._step_once()
        return self.history[-1]

    def summary(self) -> SimulationStats:
        if not self.history:
            return self._build_stats()
        return self.history[-1]

    def road_loads(self) -> dict[str, float]:
        loads: dict[str, float] = {}
        for road_id, road in self.graph.roads.items():
            loads[road_id] = len(self.road_occupancy.get(road_id, set())) / road.effective_capacity()
        return loads

    def peak_road_loads(self) -> dict[str, float]:
        return dict(self.road_peak_loads)

    def _step_once(self) -> None:
        self.tick += 1
        self.sim_time_s += self.tick_seconds
        if self.auto_time:
            self.minute_of_day = int((self.minute_of_day + (self.tick_seconds * self.time_speed_multiplier / 60)) % (24 * 60))

        for vehicle in self.vehicles.values():
            if vehicle.state in {"arrived", "stuck"}:
                continue
            if vehicle.state == "pending":
                if self.sim_time_s >= vehicle.departure_time_s:
                    self._try_depart(vehicle)
                continue
            if vehicle.state == "queued":
                vehicle.elapsed_s += self.tick_seconds
                vehicle.wait_time_s += self.tick_seconds
                self._try_advance_from_queue(vehicle)
                continue
            road_id = vehicle.current_road_id
            if road_id is None:
                vehicle.state = "arrived"
                continue

            road = self.graph.roads[road_id]
            self._maybe_reroute_ahead(vehicle, road_id)
            vehicle.elapsed_s += self.tick_seconds
            vehicle_count = len(self.road_occupancy.get(road_id, set()))
            time_multiplier = self.time_profile.speed_multiplier_for_road(road, self.minute_of_day)
            speed_mps = road.effective_speed_kph(vehicle_count, time_multiplier=time_multiplier) * 1000 / 3600
            vehicle.progress_m += speed_mps * self.tick_seconds

            if vehicle.progress_m < road.length_m:
                vehicle.state = "moving"
                continue

            vehicle.progress_m = 0.0
            current_node = road.end_node

            if current_node == vehicle.destination_node:
                self.road_occupancy[road_id].discard(vehicle.vehicle_id)
                vehicle.route_nodes = [current_node]
                vehicle.route_roads = []
                vehicle.current_road_index = 0
                vehicle.state = "arrived"
                continue

            try:
                path = self.graph.shortest_path(
                    current_node,
                    vehicle.destination_node,
                    algorithm=self.routing_algorithm,
                    road_loads={road_id: len(occupancy) for road_id, occupancy in self.road_occupancy.items()},
                )
            except ValueError:
                vehicle.state = "stuck"
                vehicle.route_nodes = [current_node]
                vehicle.route_roads = []
                vehicle.current_road_index = 0
                continue

            next_road_id = path.roads[0] if path.roads else None
            if next_road_id is not None:
                if self._road_has_space(next_road_id):
                    self.road_occupancy[road_id].discard(vehicle.vehicle_id)
                    vehicle.route_nodes = path.nodes
                    vehicle.route_roads = path.roads
                    vehicle.current_road_index = 0
                    self.road_occupancy.setdefault(next_road_id, set()).add(vehicle.vehicle_id)
                    vehicle.state = "moving"
                    if self.reroute_on_change:
                        vehicle.reroutes += 1
                else:
                    vehicle.state = "queued"
                    vehicle.progress_m = road.length_m

        current_loads = self.road_loads()
        for road_id, load in current_loads.items():
            self.road_peak_loads[road_id] = max(self.road_peak_loads.get(road_id, 0.0), load)
        if current_loads:
            self.network_load_samples.append(sum(current_loads.values()) / len(current_loads))

        self.history.append(self._build_stats())

    def _assign_route(self, vehicle: Vehicle, start_node: str, count_as_reroute: bool) -> None:
        path = self.graph.shortest_path(
            start_node,
            vehicle.destination_node,
            algorithm=self.routing_algorithm,
            road_loads={road_id: len(occupancy) for road_id, occupancy in self.road_occupancy.items()},
        )
        vehicle.route_nodes = path.nodes
        vehicle.route_roads = path.roads
        vehicle.current_road_index = 0
        vehicle.progress_m = 0.0
        vehicle.state = "moving" if vehicle.route_roads else "arrived"
        if count_as_reroute:
            vehicle.reroutes += 1

    def _try_depart(self, vehicle: Vehicle) -> None:
        road_id = vehicle.current_road_id
        if road_id is None:
            vehicle.state = "arrived"
            return
        if self._road_has_space(road_id):
            self.road_occupancy.setdefault(road_id, set()).add(vehicle.vehicle_id)
            vehicle.state = "moving"
            return
        vehicle.state = "pending"
        vehicle.wait_time_s += self.tick_seconds

    def _try_advance_from_queue(self, vehicle: Vehicle) -> None:
        current_road_id = vehicle.current_road_id
        if current_road_id is None:
            vehicle.state = "arrived"
            return

        current_node = self.graph.roads[current_road_id].end_node
        if current_node == vehicle.destination_node:
            self.road_occupancy[current_road_id].discard(vehicle.vehicle_id)
            vehicle.route_nodes = [current_node]
            vehicle.route_roads = []
            vehicle.current_road_index = 0
            vehicle.state = "arrived"
            return

        try:
            path = self.graph.shortest_path(
                current_node,
                vehicle.destination_node,
                algorithm=self.routing_algorithm,
                road_loads={road_id: len(occupancy) for road_id, occupancy in self.road_occupancy.items()},
            )
        except ValueError:
            self.road_occupancy[current_road_id].discard(vehicle.vehicle_id)
            vehicle.state = "stuck"
            vehicle.route_nodes = [current_node]
            vehicle.route_roads = []
            vehicle.current_road_index = 0
            return

        next_road_id = path.roads[0] if path.roads else None
        if next_road_id is not None and self._road_has_space(next_road_id):
            self.road_occupancy[current_road_id].discard(vehicle.vehicle_id)
            vehicle.route_nodes = path.nodes
            vehicle.route_roads = path.roads
            vehicle.current_road_index = 0
            self.road_occupancy.setdefault(next_road_id, set()).add(vehicle.vehicle_id)
            vehicle.progress_m = 0.0
            vehicle.state = "moving"
            if self.reroute_on_change:
                vehicle.reroutes += 1
            return

        vehicle.state = "queued"
        vehicle.progress_m = self.graph.roads[current_road_id].length_m

    def _maybe_reroute_ahead(self, vehicle: Vehicle, current_road_id: str) -> None:
        if self.reroute_interval_ticks <= 0:
            return
        if self.tick % self.reroute_interval_ticks != 0:
            return
        if vehicle.behavior == "cautious" and self.tick % (self.reroute_interval_ticks * 2) != 0:
            return
        current_road = self.graph.roads[current_road_id]
        upcoming = vehicle.route_roads[vehicle.current_road_index + 1 : vehicle.current_road_index + 5]
        if not upcoming:
            return
        loads = self.road_loads()
        blocked_or_hot = [
            road_id
            for road_id in upcoming
            if road_id in self.graph.roads
            and (not self.graph.roads[road_id].is_open or loads.get(road_id, 0.0) >= self._reroute_load_threshold(vehicle))
        ]
        if not blocked_or_hot:
            return
        try:
            path = self.graph.shortest_path(
                current_road.end_node,
                vehicle.destination_node,
                algorithm=self.routing_algorithm,
                road_loads={road_id: len(occupancy) for road_id, occupancy in self.road_occupancy.items()},
            )
        except ValueError:
            return
        new_remaining = path.roads
        if not new_remaining or new_remaining == upcoming[: len(new_remaining)]:
            return
        vehicle.route_nodes = [current_road.start_node, *path.nodes]
        vehicle.route_roads = [current_road_id, *new_remaining]
        vehicle.current_road_index = 0
        vehicle.reroutes += 1

    def _reroute_load_threshold(self, vehicle: Vehicle) -> float:
        if vehicle.behavior == "aggressive_reroute":
            return 0.55
        if vehicle.behavior == "avoid_congestion":
            return 0.65
        return 0.82

    def _road_has_space(self, road_id: str) -> bool:
        road = self.graph.roads[road_id]
        return road.is_open and len(self.road_occupancy.get(road_id, set())) < road.effective_capacity()

    def _build_stats(self) -> SimulationStats:
        active = sum(1 for vehicle in self.vehicles.values() if vehicle.state in {"moving", "queued"})
        arrived = sum(1 for vehicle in self.vehicles.values() if vehicle.state == "arrived")
        stuck = sum(1 for vehicle in self.vehicles.values() if vehicle.state == "stuck")
        finished_times = [vehicle.elapsed_s for vehicle in self.vehicles.values() if vehicle.state == "arrived"]
        average_trip_time = sum(finished_times) / len(finished_times) if finished_times else 0.0
        loads = list(self.road_peak_loads.values())
        max_load = max(loads, default=0.0)
        average_load = sum(self.network_load_samples) / len(self.network_load_samples) if self.network_load_samples else 0.0
        return SimulationStats(
            tick=self.tick,
            sim_time_s=self.sim_time_s,
            active_vehicles=active,
            arrived_vehicles=arrived,
            stuck_vehicles=stuck,
            average_trip_time_s=average_trip_time,
            max_road_load=max_load,
            average_road_load=average_load,
        )
