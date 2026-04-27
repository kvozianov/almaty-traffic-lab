from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .models import Node, Road
from .network import CityGraph, build_demo_city_graph, load_graph_from_osm_bbox, load_graph_from_osm_place


DEFAULT_CACHE_DIR = Path("cache/graphs")

PRESETS: dict[str, dict[str, Any]] = {
    "demo": {
        "id": "demo",
        "name": "Demo grid",
        "kind": "demo",
        "center": [1.0, 1.0],
        "zoom": 13,
        "description": "Small synthetic grid for fast tests.",
    },
    "almaty_center": {
        "id": "almaty_center",
        "name": "Almaty center",
        "kind": "bbox",
        "bbox": [43.245, 43.240, 76.950, 76.940],
        "center": [43.2425, 76.945],
        "zoom": 16,
        "description": "Verified small real OSM area for quick runs.",
    },
    "full_almaty": {
        "id": "full_almaty",
        "name": "Full Almaty",
        "kind": "place",
        "place": "Almaty, Kazakhstan",
        "center": [43.238, 76.945],
        "zoom": 11,
        "description": "Full-city OSM graph. First run can take a while, then it is cached.",
    },
    "full_almaty_fast": {
        "id": "full_almaty_fast",
        "name": "Full Almaty fast",
        "kind": "alias",
        "source": "full_almaty",
        "center": [43.238, 76.945],
        "zoom": 11,
        "description": "City-wide reduced graph for responsive dashboard previews.",
    },
}


def list_presets() -> list[dict[str, Any]]:
    return [dict(preset) for preset in PRESETS.values()]


def load_preset_graph(preset_id: str, refresh: bool = False, cache_dir: Path = DEFAULT_CACHE_DIR) -> CityGraph:
    if preset_id not in PRESETS:
        raise ValueError(f"Unknown preset: {preset_id}")

    preset = PRESETS[preset_id]
    if preset["kind"] == "demo":
        return build_demo_city_graph()

    cache_path = cache_dir / f"{preset_id}.json"
    if cache_path.exists() and not refresh:
        return load_graph_json(cache_path)

    if preset["kind"] == "alias":
        return load_preset_graph(preset["source"], refresh=refresh, cache_dir=cache_dir)

    try:
        if preset["kind"] == "bbox":
            north, south, east, west = preset["bbox"]
            graph = load_graph_from_osm_bbox(north, south, east, west)
        elif preset["kind"] == "place":
            graph = load_graph_from_osm_place(preset["place"])
        else:
            raise ValueError(f"Unsupported preset kind: {preset['kind']}")
    except Exception as exc:
        if cache_path.exists():
            return load_graph_json(cache_path)
        raise RuntimeError(
            f"Could not load OSM graph for '{preset_id}'. Try a smaller preset first or check network access. {exc}"
        ) from exc

    save_graph_json(graph, cache_path)
    return graph


def reduce_graph_for_preview(graph: CityGraph, max_roads: int = 12000) -> CityGraph:
    if len(graph.roads) <= max_roads:
        return graph

    sorted_roads = sorted(
        graph.roads.values(),
        key=lambda road: (
            _road_bucket(graph, road),
            -road.length_m,
            -road.capacity,
        ),
    )
    stride = max(1, len(sorted_roads) // max_roads)
    sampled = sorted_roads[::stride][:max_roads]
    if len(sampled) < max_roads:
        sampled = sorted_roads[:max_roads]
    sorted_roads = sampled
    used_nodes = {road.start_node for road in sorted_roads} | {road.end_node for road in sorted_roads}
    reduced = CityGraph()
    for node_id in used_nodes:
        node = graph.nodes[node_id]
        reduced.add_node(node.node_id, x=node.x, y=node.y, label=node.label)
    for road in sorted_roads:
        reduced.add_road(
            road_id=road.road_id,
            start_node=road.start_node,
            end_node=road.end_node,
            length_m=road.length_m,
            max_speed_kph=road.max_speed_kph,
            capacity=road.capacity,
            signal_delay_s=road.signal_delay_s,
            is_open=road.is_open,
            metadata=road.metadata,
        )
    return reduced


def _road_bucket(graph: CityGraph, road: Road) -> tuple[int, int]:
    start = graph.nodes[road.start_node]
    return int(start.x * 100), int(start.y * 100)


def save_graph_json(graph: CityGraph, path: str | Path) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "nodes": [asdict(node) for node in graph.nodes.values()],
        "roads": [_road_to_dict(road) for road in graph.roads.values()],
    }
    output.write_text(json.dumps(payload, ensure_ascii=True), encoding="utf-8")
    return output


def load_graph_json(path: str | Path) -> CityGraph:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    graph = CityGraph()
    for raw_node in payload["nodes"]:
        node = Node(**raw_node)
        graph.add_node(node.node_id, x=node.x, y=node.y, label=node.label)
    for raw_road in payload["roads"]:
        graph.add_road(
            road_id=raw_road["road_id"],
            start_node=raw_road["start_node"],
            end_node=raw_road["end_node"],
            length_m=raw_road["length_m"],
            max_speed_kph=raw_road["max_speed_kph"],
            capacity=raw_road["capacity"],
            signal_delay_s=raw_road.get("signal_delay_s", 0.0),
            is_open=raw_road.get("is_open", True),
            metadata=raw_road.get("metadata", {}),
        )
        road = graph.roads[raw_road["road_id"]]
        road.speed_modifier = raw_road.get("speed_modifier", 1.0)
        road.capacity_modifier = raw_road.get("capacity_modifier", 1.0)
    return graph


def _road_to_dict(road: Road) -> dict[str, Any]:
    return {
        "road_id": road.road_id,
        "start_node": road.start_node,
        "end_node": road.end_node,
        "length_m": road.length_m,
        "max_speed_kph": road.max_speed_kph,
        "capacity": road.capacity,
        "signal_delay_s": road.signal_delay_s,
        "is_open": road.is_open,
        "speed_modifier": road.speed_modifier,
        "capacity_modifier": road.capacity_modifier,
        "metadata": _json_safe(road.metadata),
    }


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)
