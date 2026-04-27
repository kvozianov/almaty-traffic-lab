from __future__ import annotations

import random
from collections import deque

from .models import Vehicle
from .network import CityGraph


def generate_vehicle_demand(
    graph: CityGraph,
    vehicle_count: int,
    seed: int = 7,
    horizon_s: float = 900.0,
    surge_node: str | None = None,
    surge_share: float = 0.35,
) -> list[Vehicle]:
    rng = random.Random(seed)
    candidate_nodes = _largest_reachable_pool(graph)
    if len(candidate_nodes) < 2:
        raise ValueError("Graph must contain at least two routable nodes")
    if len(candidate_nodes) > 4000:
        candidate_nodes = _sample_spread_nodes(graph, candidate_nodes, limit=4000)

    vehicles: list[Vehicle] = []
    attempts = 0
    max_attempts = max(vehicle_count * 30, 120)
    while len(vehicles) < vehicle_count and attempts < max_attempts:
        attempts += 1
        use_surge = surge_node in graph.nodes and rng.random() < surge_share
        start = surge_node if use_surge else rng.choice(candidate_nodes)
        destination = rng.choice(candidate_nodes)
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
            )
        )

    if len(vehicles) < vehicle_count:
        raise ValueError(f"Only generated {len(vehicles)} valid trips out of requested {vehicle_count}")
    vehicles.sort(key=lambda vehicle: vehicle.departure_time_s)
    return vehicles


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
