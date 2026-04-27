from __future__ import annotations

from dataclasses import replace

from .models import SimulationStats, Vehicle
from .network import CityGraph


class TrafficSimulation:
    def __init__(
        self,
        graph: CityGraph,
        tick_seconds: int = 10,
        routing_algorithm: str = "dijkstra",
        reroute_on_change: bool = True,
    ) -> None:
        self.graph = graph
        self.tick_seconds = tick_seconds
        self.routing_algorithm = routing_algorithm
        self.reroute_on_change = reroute_on_change
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
            vehicle.elapsed_s += self.tick_seconds
            vehicle_count = len(self.road_occupancy.get(road_id, set()))
            speed_mps = road.effective_speed_kph(vehicle_count) * 1000 / 3600
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
