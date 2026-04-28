from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class Node:
    node_id: str
    x: float = 0.0
    y: float = 0.0
    label: str | None = None


@dataclass(slots=True)
class TrafficSignal:
    signal_id: str
    node_id: str
    lat: float
    lng: float
    cycle_s: float = 74.0
    green_s: float = 35.0
    yellow_s: float = 4.0
    red_s: float = 35.0
    delay_s: float = 12.0


@dataclass(slots=True)
class Road:
    road_id: str
    start_node: str
    end_node: str
    length_m: float
    max_speed_kph: float
    capacity: int
    lanes: int = 1
    road_class: str = "road"
    signal_delay_s: float = 0.0
    is_open: bool = True
    speed_modifier: float = 1.0
    capacity_modifier: float = 1.0
    metadata: dict[str, object] = field(default_factory=dict)

    def effective_capacity(self) -> int:
        return max(1, int(round(self.capacity * self.capacity_modifier)))

    def effective_speed_kph(self, vehicle_count: int, time_multiplier: float = 1.0) -> float:
        load = vehicle_count / self.effective_capacity()
        congestion_factor = max(0.15, 1.0 - 0.85 * load)
        return max(1.0, self.max_speed_kph * self.speed_modifier * time_multiplier * congestion_factor)

    def travel_time_s(self, vehicle_count: int = 0, time_multiplier: float = 1.0) -> float:
        speed_mps = self.effective_speed_kph(vehicle_count, time_multiplier=time_multiplier) * 1000 / 3600
        return (self.length_m / speed_mps) + self.signal_delay_s


@dataclass(slots=True)
class Vehicle:
    vehicle_id: str
    start_node: str
    destination_node: str
    departure_time_s: float = 0.0
    behavior: str = "normal"
    origin_zone_id: str | None = None
    destination_zone_id: str | None = None
    spawn_road_id: str | None = None
    spawn_ratio: float = 0.0
    route_nodes: list[str] = field(default_factory=list)
    route_roads: list[str] = field(default_factory=list)
    current_road_index: int = 0
    progress_m: float = 0.0
    elapsed_s: float = 0.0
    wait_time_s: float = 0.0
    reroutes: int = 0
    state: str = "pending"

    @property
    def current_road_id(self) -> str | None:
        if 0 <= self.current_road_index < len(self.route_roads):
            return self.route_roads[self.current_road_index]
        return None

    def is_arrived(self) -> bool:
        return self.state == "arrived"


@dataclass(slots=True)
class SimulationStats:
    tick: int
    sim_time_s: float
    active_vehicles: int
    arrived_vehicles: int
    stuck_vehicles: int
    average_trip_time_s: float
    max_road_load: float
    average_road_load: float
