from __future__ import annotations

import random
from collections import deque

from .ai_policy import AIDriverPolicy, build_policy
from .models import Vehicle
from .network import CityGraph
from .zones import TrafficZone, build_zone_index, choose_od_zones, load_zones


def generate_vehicle_demand(
    graph: CityGraph,
    vehicle_count: int,
    seed: int = 7,
    horizon_s: float = 900.0,
    surge_node: str | None = None,
    surge_share: float = 0.35,
    policy: AIDriverPolicy | None = None,
    minute_of_day: int = 17 * 60,
    road_loads: dict[str, float] | None = None,
    demand_mode: str = "random_roads",
    zones: list[TrafficZone] | None = None,
    time_preset: str | None = None,
) -> list[Vehicle]:
    rng = random.Random(seed)
    policy = policy or build_policy("heuristic")
    road_loads = road_loads or {}
    candidate_nodes = _largest_reachable_pool(graph)
    if len(candidate_nodes) < 2:
        raise ValueError("Graph must contain at least two routable nodes")
    if len(candidate_nodes) > 4000:
        candidate_nodes = _sample_spread_nodes(graph, candidate_nodes, limit=4000)
    zone_index = None
    if demand_mode == "od_zones":
        zones = zones or load_zones()
        zone_index = build_zone_index(graph, zones, limit=96)

    vehicles: list[Vehicle] = []
    attempts = 0
    max_attempts = max(vehicle_count * 30, 120)
    while len(vehicles) < vehicle_count and attempts < max_attempts:
        attempts += 1
        origin_zone_id = None
        destination_zone_id = None
        if demand_mode == "od_zones" and zones and zone_index:
            trip = _choose_zone_trip(graph, zones, zone_index, rng, minute_of_day, time_preset)
            if trip is None:
                continue
            start, destination, behavior, spawn_road_id, spawn_ratio, origin_zone_id, destination_zone_id = trip
        elif surge_node in graph.nodes and rng.random() < surge_share:
            start = surge_node
            destination = rng.choice(candidate_nodes)
            behavior = "avoid_congestion"
            spawn_road_id = None
            spawn_ratio = 0.0
        else:
            decision = policy.choose_trip(graph, rng, road_loads=road_loads, minute_of_day=minute_of_day)
            start = decision.start_node
            destination = decision.destination_node
            behavior = decision.behavior
            spawn_road_id = decision.spawn_road_id
            spawn_ratio = decision.spawn_ratio
        if start == destination:
            continue
        try:
            graph.shortest_path(start, destination, algorithm="astar")
        except ValueError:
            continue
        departure_time_s = rng.uniform(0, max(horizon_s, 1.0))
        vehicles.append(
            Vehicle(
                vehicle_id=f"car-{len(vehicles) + 1}",
                start_node=start,
                destination_node=destination,
                departure_time_s=departure_time_s,
                behavior=behavior,
                spawn_road_id=spawn_road_id,
                spawn_ratio=spawn_ratio,
                origin_zone_id=origin_zone_id,
                destination_zone_id=destination_zone_id,
            )
        )

    if len(vehicles) < vehicle_count:
        raise ValueError(f"Only generated {len(vehicles)} valid trips out of requested {vehicle_count}")
    vehicles.sort(key=lambda vehicle: vehicle.departure_time_s)
    return vehicles


def _choose_zone_trip(
    graph: CityGraph,
    zones: list[TrafficZone],
    zone_index: dict[str, dict[str, list[str]]],
    rng: random.Random,
    minute_of_day: int,
    time_preset: str | None,
) -> tuple[str, str, str, str | None, float, str, str] | None:
    origin_zone, destination_zone = choose_od_zones(zones, rng, minute_of_day, preset=time_preset)
    origin_roads = list(zone_index.get(origin_zone.zone_id, {}).get("roads", []))
    destination_nodes = list(zone_index.get(destination_zone.zone_id, {}).get("nodes", []))
    if not origin_roads or not destination_nodes:
        return None
    rng.shuffle(origin_roads)
    rng.shuffle(destination_nodes)
    behaviors = ["normal", "normal", "avoid_congestion", "aggressive_reroute", "cautious"]
    for road_id in origin_roads[:12]:
        road = graph.roads.get(road_id)
        if road is None or not road.is_open:
            continue
        start = road.end_node
        for destination in destination_nodes[:12]:
            if start == destination:
                continue
            try:
                graph.shortest_path(start, destination, algorithm="astar")
            except ValueError:
                continue
            return (
                start,
                destination,
                rng.choice(behaviors),
                road_id,
                rng.uniform(0.05, 0.95),
                origin_zone.zone_id,
                destination_zone.zone_id,
            )
    return None


def _sample_spread_nodes(graph: CityGraph, node_ids: list[str], limit: int) -> list[str]:
    sorted_nodes = sorted(node_ids, key=lambda node_id: (graph.nodes[node_id].x, graph.nodes[node_id].y))
    stride = max(1, len(sorted_nodes) // limit)
    return sorted_nodes[::stride][:limit]


def _largest_reachable_pool(graph: CityGraph) -> list[str]:
    adjacency: dict[str, set[str]] = {}
    for road in graph.roads.values():
        adjacency.setdefault(road.start_node, set()).add(road.end_node)
        adjacency.setdefault(road.end_node, set()).add(road.start_node)

    visited: set[str] = set()
    largest: set[str] = set()
    for node_id in adjacency:
        if node_id in visited:
            continue
        component: set[str] = set()
        queue = deque([node_id])
        visited.add(node_id)
        while queue:
            current = queue.popleft()
            component.add(current)
            for neighbor in adjacency.get(current, set()):
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)
        if len(component) > len(largest):
            largest = component
    return [node_id for node_id in largest if graph.outgoing.get(node_id)]
