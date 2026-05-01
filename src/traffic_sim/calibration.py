from __future__ import annotations

import json
import re
from collections import deque
from pathlib import Path
from typing import Any

from .network import CityGraph


DEFAULT_CALIBRATION_PATH = Path("data/calibration/almaty_calibration_layer.json")


def load_calibration_layer(path: str | Path = DEFAULT_CALIBRATION_PATH) -> dict[str, object]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def match_calibration_to_graph(graph: CityGraph, path: str | Path = DEFAULT_CALIBRATION_PATH) -> dict[str, object]:
    layer = load_calibration_layer(path)
    road_text = {road_id: _road_haystack(road_id, road.metadata.get("name")) for road_id, road in graph.roads.items()}
    node_roads = _build_node_roads(graph)
    segments = [match_segment(graph, item, road_text, node_roads) for item in layer.get("segments", [])]
    intersections = [match_intersection(graph, item, road_text, node_roads) for item in layer.get("must_calibrate_intersections", [])]
    return {
        "segments": segments,
        "intersections": intersections,
        "summary": {
            "segmentsMatched": sum(1 for item in segments if item.get("matchedRoadIds")),
            "intersectionsMatched": sum(1 for item in intersections if item.get("matched")),
            "segmentCount": len(segments),
            "intersectionCount": len(intersections),
        },
    }


def calibration_stats_from_roads(
    roads: list[dict[str, object]],
    calibration_layer: dict[str, object],
    limit: int = 10,
) -> dict[str, object]:
    road_by_id = {str(road["id"]): road for road in roads}
    segment_rows = []
    for segment in calibration_layer.get("segments", []):
        matched = [road_by_id[road_id] for road_id in segment.get("matchedRoadIds", []) if road_id in road_by_id]
        if not matched:
            continue
        avg_load = sum(float(road.get("load", 0.0)) for road in matched) / len(matched)
        avg_speed = sum(float(road.get("maxSpeedKph", 0.0)) * float(road.get("speedModifier", 1.0)) for road in matched) / len(matched)
        segment_rows.append(
            {
                "id": segment["id"],
                "name": segment["name"],
                "rank": segment.get("rank"),
                "averageLoad": round(avg_load, 4),
                "estimatedSpeedKph": round(avg_speed, 1),
                "congestionIndex": float(segment.get("congestion_index", 0.0)),
                "matchedRoads": len(matched),
            }
        )
    segment_rows.sort(key=lambda item: (item["averageLoad"], item["congestionIndex"]), reverse=True)

    intersection_rows = []
    for item in calibration_layer.get("intersections", []):
        road_ids = item.get("matchedRoadIds", [])
        matched = [road_by_id[road_id] for road_id in road_ids if road_id in road_by_id]
        if not matched:
            continue
        avg_load = sum(float(road.get("load", 0.0)) for road in matched) / len(matched)
        intersection_rows.append(
            {
                "id": item["id"],
                "name": item["name"],
                "priority": float(item.get("priority", 0.0)),
                "averageLoad": round(avg_load, 4),
                "matchedRoads": len(matched),
            }
        )
    intersection_rows.sort(key=lambda item: (item["averageLoad"], item["priority"]), reverse=True)

    return {
        "segmentRows": segment_rows[:limit],
        "intersectionRows": intersection_rows[:limit],
        "summary": calibration_layer.get("summary", {}),
    }


def match_segment(
    graph: CityGraph,
    item: dict[str, object],
    road_text: dict[str, str],
    node_roads: dict[str, set[str]],
) -> dict[str, object]:
    corridor_tags = [str(tag).lower() for tag in item.get("corridor_tags", [])]
    from_tags = [str(tag).lower() for tag in item.get("from_tags", [])]
    to_tags = [str(tag).lower() for tag in item.get("to_tags", [])]
    corridor_road_ids = [road_id for road_id, haystack in road_text.items() if _contains_any(haystack, corridor_tags)] if corridor_tags else []
    matched_road_ids = []
    if corridor_road_ids and from_tags and to_tags:
        start_nodes = _intersection_nodes_from_tags(corridor_road_ids, from_tags, node_roads, road_text)
        end_nodes = _intersection_nodes_from_tags(corridor_road_ids, to_tags, node_roads, road_text)
        matched_road_ids = _path_along_corridor(graph, corridor_road_ids, start_nodes, end_nodes)
    if not matched_road_ids:
        seed_tags = corridor_tags or from_tags or to_tags
        matched_road_ids = [road_id for road_id, haystack in road_text.items() if _contains_any(haystack, seed_tags)][:20]
    coords = _segment_coords(graph, matched_road_ids)
    return {
        **item,
        "matchedRoadIds": matched_road_ids,
        "matched": bool(matched_road_ids),
        "coords": coords,
    }


def match_intersection(
    graph: CityGraph,
    item: dict[str, object],
    road_text: dict[str, str],
    node_roads: dict[str, set[str]],
) -> dict[str, object]:
    tags = [str(tag).lower() for tag in item.get("street_tags", [])]
    best_node = None
    best_score = -1
    matched_roads: set[str] = set()
    for node_id, road_ids in node_roads.items():
        score = 0
        node_match_roads: set[str] = set()
        for tag in tags:
            local = [road_id for road_id in road_ids if tag and tag in road_text.get(road_id, "")]
            if local:
                score += 1
                node_match_roads.update(local)
        if score > best_score:
            best_score = score
            best_node = node_id
            matched_roads = node_match_roads
    lat = None
    lng = None
    if best_node is not None and best_score >= min(2, len(tags)):
        node = graph.nodes[best_node]
        lng = node.x
        lat = node.y
    return {
        **item,
        "matched": best_node is not None and best_score >= min(2, len(tags)),
        "nodeId": best_node,
        "lat": lat,
        "lng": lng,
        "matchedRoadIds": sorted(matched_roads),
    }


def _road_haystack(road_id: str, road_name: object) -> str:
    return _normalize(f"{road_id} {road_name or ''}")


def _normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def _contains_any(haystack: str, tokens: list[str]) -> bool:
    return any(token and token in haystack for token in tokens)


def _build_node_roads(graph: CityGraph) -> dict[str, set[str]]:
    node_roads: dict[str, set[str]] = {}
    for road_id, road in graph.roads.items():
        node_roads.setdefault(road.start_node, set()).add(road_id)
        node_roads.setdefault(road.end_node, set()).add(road_id)
    return node_roads


def _intersection_nodes_from_tags(
    corridor_road_ids: list[str],
    tags: list[str],
    node_roads: dict[str, set[str]],
    road_text: dict[str, str],
) -> list[str]:
    corridor_set = set(corridor_road_ids)
    nodes = []
    for node_id, road_ids in node_roads.items():
        if not corridor_set.intersection(road_ids):
            continue
        cross_roads = road_ids - corridor_set
        if any(_contains_any(road_text.get(road_id, ""), tags) for road_id in cross_roads):
            nodes.append(node_id)
    return nodes


def _path_along_corridor(
    graph: CityGraph,
    corridor_road_ids: list[str],
    start_nodes: list[str],
    end_nodes: list[str],
) -> list[str]:
    if not start_nodes or not end_nodes:
        return []
    end_set = set(end_nodes)
    allowed = set(corridor_road_ids)
    adjacency: dict[str, list[tuple[str, str]]] = {}
    for road_id in allowed:
        road = graph.roads[road_id]
        adjacency.setdefault(road.start_node, []).append((road.end_node, road_id))
        adjacency.setdefault(road.end_node, []).append((road.start_node, road_id))
    queue = deque([(node_id, []) for node_id in start_nodes])
    seen = set(start_nodes)
    while queue:
        node_id, route = queue.popleft()
        if node_id in end_set and route:
            return route
        for next_node, road_id in adjacency.get(node_id, []):
            if (node_id, next_node, road_id) in seen:
                continue
            marker = (node_id, next_node, road_id)
            seen.add(marker)
            queue.append((next_node, [*route, road_id]))
    return []


def _segment_coords(graph: CityGraph, road_ids: list[str]) -> list[list[float]]:
    coords: list[list[float]] = []
    seen: set[tuple[float, float]] = set()
    for road_id in road_ids:
        for lng, lat in graph.road_geometry(road_id):
            point = (lat, lng)
            if point in seen:
                continue
            seen.add(point)
            coords.append([lat, lng])
    return coords
