from __future__ import annotations

from dataclasses import dataclass
from heapq import heappop, heappush
from math import dist
from typing import Iterable

from .models import Node, Road


@dataclass(slots=True)
class PathResult:
    nodes: list[str]
    roads: list[str]
    total_cost_s: float


class CityGraph:
    def __init__(self) -> None:
        self.nodes: dict[str, Node] = {}
        self.roads: dict[str, Road] = {}
        self.outgoing: dict[str, list[str]] = {}
        self._max_speed_kph: float = 60.0

    def add_node(self, node_id: str, x: float = 0.0, y: float = 0.0, label: str | None = None) -> None:
        self.nodes[node_id] = Node(node_id=node_id, x=x, y=y, label=label)
        self.outgoing.setdefault(node_id, [])

    def add_road(
        self,
        road_id: str,
        start_node: str,
        end_node: str,
        length_m: float,
        max_speed_kph: float,
        capacity: int,
        signal_delay_s: float = 0.0,
        is_open: bool = True,
        metadata: dict[str, object] | None = None,
    ) -> None:
        if start_node not in self.nodes or end_node not in self.nodes:
            raise KeyError(f"Unknown road endpoints: {start_node} -> {end_node}")
        road = Road(
            road_id=road_id,
            start_node=start_node,
            end_node=end_node,
            length_m=length_m,
            max_speed_kph=max_speed_kph,
            capacity=capacity,
            signal_delay_s=signal_delay_s,
            is_open=is_open,
            metadata=metadata or {},
        )
        self.roads[road_id] = road
        self.outgoing.setdefault(start_node, []).append(road_id)
        self._max_speed_kph = max(self._max_speed_kph, max_speed_kph)

    def iter_open_roads_from(self, node_id: str) -> Iterable[Road]:
        for road_id in self.outgoing.get(node_id, []):
            road = self.roads[road_id]
            if road.is_open:
                yield road

    def road_geometry(self, road_id: str) -> list[tuple[float, float]]:
        road = self.roads[road_id]
        geometry = road.metadata.get("geometry")
        if isinstance(geometry, list) and len(geometry) >= 2:
            return [(float(x), float(y)) for x, y in geometry]
        start = self.nodes[road.start_node]
        end = self.nodes[road.end_node]
        return [(start.x, start.y), (end.x, end.y)]

    def shortest_path(
        self,
        start_node: str,
        destination_node: str,
        algorithm: str = "dijkstra",
        road_loads: dict[str, int] | None = None,
    ) -> PathResult:
        if start_node not in self.nodes or destination_node not in self.nodes:
            raise KeyError("Start or destination node does not exist in the graph")
        if start_node == destination_node:
            return PathResult(nodes=[start_node], roads=[], total_cost_s=0.0)

        if algorithm not in {"dijkstra", "astar"}:
            raise ValueError("algorithm must be 'dijkstra' or 'astar'")

        road_loads = road_loads or {}
        queue: list[tuple[float, float, str]] = []
        heappush(queue, (0.0, 0.0, start_node))
        best_cost: dict[str, float] = {start_node: 0.0}
        previous_node: dict[str, str] = {}
        previous_road: dict[str, str] = {}

        while queue:
            _, current_cost, current = heappop(queue)
            if current == destination_node:
                break
            if current_cost > best_cost.get(current, float("inf")):
                continue

            for road in self.iter_open_roads_from(current):
                next_cost = current_cost + road.travel_time_s(road_loads.get(road.road_id, 0))
                if next_cost >= best_cost.get(road.end_node, float("inf")):
                    continue
                best_cost[road.end_node] = next_cost
                previous_node[road.end_node] = current
                previous_road[road.end_node] = road.road_id
                estimate = next_cost
                if algorithm == "astar":
                    estimate += self._heuristic_s(road.end_node, destination_node)
                heappush(queue, (estimate, next_cost, road.end_node))

        if destination_node not in best_cost:
            raise ValueError(f"No route from {start_node} to {destination_node}")

        nodes: list[str] = [destination_node]
        roads: list[str] = []
        current = destination_node
        while current != start_node:
            roads.append(previous_road[current])
            current = previous_node[current]
            nodes.append(current)
        nodes.reverse()
        roads.reverse()
        return PathResult(nodes=nodes, roads=roads, total_cost_s=best_cost[destination_node])

    def _heuristic_s(self, current_node: str, destination_node: str) -> float:
        current = self.nodes[current_node]
        target = self.nodes[destination_node]
        straight_m = dist((current.x, current.y), (target.x, target.y))
        max_speed_mps = self._max_speed_kph * 1000 / 3600
        return straight_m / max_speed_mps


def build_demo_city_graph() -> CityGraph:
    graph = CityGraph()
    coordinates = {
        "northwest": (0.0, 2.0),
        "north": (1.0, 2.0),
        "northeast": (2.0, 2.0),
        "west": (0.0, 1.0),
        "center": (1.0, 1.0),
        "east": (2.0, 1.0),
        "southwest": (0.0, 0.0),
        "south": (1.0, 0.0),
        "southeast": (2.0, 0.0),
    }
    for node_id, (x, y) in coordinates.items():
        graph.add_node(node_id, x=x * 1000, y=y * 1000, label=node_id.replace("_", " "))

    def add_bidirectional(base_id: str, start: str, end: str, *, length: float, speed: float, capacity: int, delay: float = 0.0) -> None:
        graph.add_road(
            f"{base_id}_ab",
            start,
            end,
            length_m=length,
            max_speed_kph=speed,
            capacity=capacity,
            signal_delay_s=delay,
        )
        graph.add_road(
            f"{base_id}_ba",
            end,
            start,
            length_m=length,
            max_speed_kph=speed,
            capacity=capacity,
            signal_delay_s=delay,
        )

    add_bidirectional("abay", "west", "center", length=1000, speed=50, capacity=18, delay=12)
    add_bidirectional("satpayev", "center", "east", length=1000, speed=45, capacity=16, delay=16)
    add_bidirectional("tole_bi", "southwest", "south", length=1000, speed=45, capacity=14, delay=14)
    add_bidirectional("ryskulov", "south", "southeast", length=1000, speed=55, capacity=22, delay=10)
    add_bidirectional("seifullin", "north", "center", length=1000, speed=40, capacity=12, delay=18)
    add_bidirectional("nazarbayev", "center", "south", length=1000, speed=35, capacity=10, delay=20)
    add_bidirectional("outer_west", "northwest", "west", length=1000, speed=50, capacity=20, delay=8)
    add_bidirectional("outer_east", "northeast", "east", length=1000, speed=50, capacity=20, delay=8)
    add_bidirectional("outer_southwest", "west", "southwest", length=1000, speed=40, capacity=12, delay=10)
    add_bidirectional("outer_southeast", "east", "southeast", length=1000, speed=40, capacity=12, delay=10)
    add_bidirectional("ring_north", "northwest", "north", length=1000, speed=55, capacity=20, delay=6)
    add_bidirectional("ring_northeast", "north", "northeast", length=1000, speed=55, capacity=20, delay=6)
    add_bidirectional("diag_sw", "southwest", "center", length=1400, speed=35, capacity=8, delay=20)
    add_bidirectional("diag_ne", "center", "northeast", length=1400, speed=35, capacity=8, delay=20)
    add_bidirectional("diag_nw", "northwest", "center", length=1400, speed=35, capacity=8, delay=20)
    add_bidirectional("diag_se", "center", "southeast", length=1400, speed=35, capacity=8, delay=20)
    return graph


def load_graph_from_osm_place(place_name: str, network_type: str = "drive") -> CityGraph:
    try:
        import osmnx as ox
    except ImportError as exc:
        raise ImportError(
            "OpenStreetMap support requires the optional 'osm' dependencies. "
            "Install them with: pip install -e .[osm]"
        ) from exc

    osm_graph = ox.graph_from_place(place_name, network_type=network_type)
    return _convert_osm_graph(osm_graph)


def load_graph_from_osm_bbox(
    north: float,
    south: float,
    east: float,
    west: float,
    network_type: str = "drive",
) -> CityGraph:
    try:
        import osmnx as ox
    except ImportError as exc:
        raise ImportError(
            "OpenStreetMap support requires the optional 'osm' dependencies. "
            "Install them with: pip install -e .[osm]"
        ) from exc

    osm_graph = ox.graph_from_bbox((west, south, east, north), network_type=network_type)
    return _convert_osm_graph(osm_graph)


def _convert_osm_graph(osm_graph) -> CityGraph:
    graph = CityGraph()

    for node_id, attrs in osm_graph.nodes(data=True):
        graph.add_node(
            str(node_id),
            x=float(attrs.get("x", 0.0)),
            y=float(attrs.get("y", 0.0)),
            label=str(node_id),
        )

    for start, end, key, attrs in osm_graph.edges(keys=True, data=True):
        length_m = float(attrs.get("length", 100.0))
        maxspeed = attrs.get("maxspeed", 50)
        if isinstance(maxspeed, list):
            maxspeed = maxspeed[0]
        try:
            max_speed_kph = float(str(maxspeed).split()[0])
        except ValueError:
            max_speed_kph = 50.0
        lane_count = attrs.get("lanes", 1)
        if isinstance(lane_count, list):
            lane_count = lane_count[0]
        try:
            lane_count_int = max(1, int(str(lane_count).split(";")[0]))
        except ValueError:
            lane_count_int = 1
        capacity = max(8, lane_count_int * 12)
        geometry = attrs.get("geometry")
        geometry_points = None
        if geometry is not None:
            geometry_points = [(float(x), float(y)) for x, y in geometry.coords]
        graph.add_road(
            road_id=f"{start}->{end}:{key}",
            start_node=str(start),
            end_node=str(end),
            length_m=length_m,
            max_speed_kph=max_speed_kph,
            capacity=capacity,
            metadata={"name": attrs.get("name"), "highway": attrs.get("highway"), "geometry": geometry_points},
        )
    return graph
