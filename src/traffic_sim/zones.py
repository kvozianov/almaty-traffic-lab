from __future__ import annotations

import json
import math
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .network import CityGraph
from .time_profiles import parse_hhmm


DEFAULT_ZONES_PATH = Path("data/zones/almaty_zones.json")
DEFAULT_OD_MATRIX_PATH = Path("data/zones/almaty_od_matrix.json")


@dataclass(slots=True)
class TrafficZone:
    zone_id: str
    name: str
    lat: float
    lng: float
    radius_m: float
    kind: str
    weights: dict[str, float]

    def weight_for_period(self, period: str) -> float:
        return max(0.05, float(self.weights.get(period, 1.0)))


def load_zones(path: str | Path = DEFAULT_ZONES_PATH) -> list[TrafficZone]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return [
        TrafficZone(
            zone_id=str(item["id"]),
            name=str(item["name"]),
            lat=float(item["lat"]),
            lng=float(item["lng"]),
            radius_m=float(item.get("radius_m", 2500)),
            kind=str(item.get("kind", "mixed")),
            weights={str(key): float(value) for key, value in dict(item.get("weights", {})).items()},
        )
        for item in payload.get("zones", [])
    ]


def load_od_matrix(path: str | Path = DEFAULT_OD_MATRIX_PATH) -> dict[str, dict[str, float]]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    matrix = payload.get("matrix", {})
    return {
        str(origin): {str(destination): float(weight) for destination, weight in dict(destinations).items()}
        for origin, destinations in dict(matrix).items()
    }


def zones_payload(zones: list[TrafficZone]) -> list[dict[str, object]]:
    return [
        {
            "id": zone.zone_id,
            "name": zone.name,
            "lat": zone.lat,
            "lng": zone.lng,
            "radiusM": zone.radius_m,
            "kind": zone.kind,
            "weights": zone.weights,
        }
        for zone in zones
    ]


def time_period_for_minute(minute_of_day: int, preset: str | None = None) -> str:
    if preset == "weekend":
        return "weekend"
    minute_of_day %= 24 * 60
    if parse_hhmm("06:30") <= minute_of_day <= parse_hhmm("10:00"):
        return "morning"
    if parse_hhmm("11:30") <= minute_of_day <= parse_hhmm("14:30"):
        return "lunch"
    if parse_hhmm("16:30") <= minute_of_day <= parse_hhmm("20:00"):
        return "evening"
    if minute_of_day >= parse_hhmm("22:00") or minute_of_day <= parse_hhmm("06:00"):
        return "night"
    return "day"


def build_zone_index(graph: CityGraph, zones: list[TrafficZone], limit: int = 80) -> dict[str, dict[str, list[str]]]:
    index: dict[str, dict[str, list[str]]] = {}
    for zone in zones:
        roads = nearest_roads_for_zone(graph, zone, limit=limit)
        nodes = nearest_nodes_for_zone(graph, zone, limit=limit)
        index[zone.zone_id] = {"roads": roads, "nodes": nodes}
    return index


def nearest_roads_for_zone(graph: CityGraph, zone: TrafficZone, limit: int = 80) -> list[str]:
    scored: list[tuple[float, str]] = []
    for road_id, road in graph.roads.items():
        if not road.is_open:
            continue
        geometry = graph.road_geometry(road_id)
        if not geometry:
            continue
        x = sum(point[0] for point in geometry) / len(geometry)
        y = sum(point[1] for point in geometry) / len(geometry)
        scored.append((_distance_to_zone_m(x, y, zone), road_id))
    scored.sort(key=lambda item: item[0])
    inside = [road_id for distance_m, road_id in scored if distance_m <= zone.radius_m]
    return (inside or [road_id for _, road_id in scored])[:limit]


def nearest_nodes_for_zone(graph: CityGraph, zone: TrafficZone, limit: int = 80) -> list[str]:
    scored: list[tuple[float, str]] = []
    for node_id, node in graph.nodes.items():
        if not graph.outgoing.get(node_id):
            continue
        scored.append((_distance_to_zone_m(node.x, node.y, zone), node_id))
    scored.sort(key=lambda item: item[0])
    inside = [node_id for distance_m, node_id in scored if distance_m <= zone.radius_m]
    return (inside or [node_id for _, node_id in scored])[:limit]


def choose_od_zones(
    zones: list[TrafficZone],
    rng: random.Random,
    minute_of_day: int,
    preset: str | None = None,
    od_matrix: dict[str, dict[str, float]] | None = None,
) -> tuple[TrafficZone, TrafficZone]:
    if len(zones) < 2:
        raise ValueError("At least two OD zones are required")
    period = time_period_for_minute(minute_of_day, preset)
    origin_weights = [_origin_weight(zone, period) for zone in zones]
    origin = rng.choices(zones, weights=origin_weights, k=1)[0]
    destination_candidates = [zone for zone in zones if zone.zone_id != origin.zone_id]
    destination_weights = [_destination_weight(origin, zone, period, od_matrix=od_matrix) for zone in destination_candidates]
    destination = rng.choices(destination_candidates, weights=destination_weights, k=1)[0]
    return origin, destination


def _origin_weight(zone: TrafficZone, period: str) -> float:
    base = zone.weight_for_period(period)
    if period == "morning" and zone.kind == "residential":
        base *= 1.7
    if period == "evening" and zone.kind in {"business", "mixed"}:
        base *= 1.45
    if period == "night" and zone.kind == "transport":
        base *= 1.2
    return base


def _destination_weight(
    origin: TrafficZone,
    zone: TrafficZone,
    period: str,
    od_matrix: dict[str, dict[str, float]] | None = None,
) -> float:
    base = zone.weight_for_period(period)
    if od_matrix:
        base *= max(0.2, float(od_matrix.get(origin.zone_id, {}).get(zone.zone_id, 1.0)))
    if period == "morning" and zone.kind in {"business", "mixed", "transport"}:
        base *= 1.7
    if period == "evening" and zone.kind == "residential":
        base *= 1.8
    if period == "weekend" and zone.kind in {"leisure", "mixed"}:
        base *= 1.5
    if period == "morning" and origin.kind in {"residential", "transport"} and zone.kind == "business":
        base *= 1.35
    if period == "evening" and origin.kind == "business" and zone.kind in {"residential", "transport"}:
        base *= 1.45
    if origin.kind == zone.kind:
        base *= 0.75
    return base


def _distance_to_zone_m(x: float, y: float, zone: TrafficZone) -> float:
    # Demo graphs use meter-like x/y coordinates. OSM graphs use lng/lat degrees.
    if abs(x) <= 180 and abs(y) <= 90:
        return haversine_m(zone.lat, zone.lng, y, x)
    zone_x, zone_y = _zone_projected_fallback(zone)
    return math.dist((x, y), (zone_x, zone_y))


def _zone_projected_fallback(zone: TrafficZone) -> tuple[float, float]:
    # Maps Almaty-ish lng/lat into the 0..2000 demo graph square.
    x = (zone.lng - 76.83) / max(77.06 - 76.83, 0.001) * 2000
    y = (zone.lat - 43.15) / max(43.36 - 43.15, 0.001) * 2000
    return x, y


def haversine_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    radius = 6371000.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lng2 - lng1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return 2 * radius * math.atan2(math.sqrt(a), math.sqrt(1 - a))
