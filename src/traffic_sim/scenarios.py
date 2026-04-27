from __future__ import annotations

from .network import CityGraph


def apply_accident(graph: CityGraph, road_id: str, capacity_factor: float = 0.3, speed_factor: float = 0.45) -> None:
    road = graph.roads[road_id]
    road.capacity_modifier *= capacity_factor
    road.speed_modifier *= speed_factor
    road.metadata["scenario"] = "accident"


def close_road_for_repair(graph: CityGraph, road_id: str) -> None:
    road = graph.roads[road_id]
    road.is_open = False
    road.metadata["scenario"] = "repair"


def retime_traffic_signal(graph: CityGraph, road_id: str, new_delay_s: float) -> None:
    road = graph.roads[road_id]
    road.signal_delay_s = new_delay_s
    road.metadata["scenario"] = "signal_retiming"


def add_bypass_road(
    graph: CityGraph,
    road_id: str,
    start_node: str,
    end_node: str,
    length_m: float,
    max_speed_kph: float,
    capacity: int,
    signal_delay_s: float = 0.0,
) -> None:
    graph.add_road(
        road_id=road_id,
        start_node=start_node,
        end_node=end_node,
        length_m=length_m,
        max_speed_kph=max_speed_kph,
        capacity=capacity,
        signal_delay_s=signal_delay_s,
        metadata={"scenario": "new_road"},
    )
