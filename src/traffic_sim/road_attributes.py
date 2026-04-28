from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


FALLBACK_SPEED_KPH = {
    "motorway": 90.0,
    "motorway_link": 60.0,
    "trunk": 80.0,
    "trunk_link": 55.0,
    "primary": 70.0,
    "primary_link": 50.0,
    "secondary": 60.0,
    "secondary_link": 45.0,
    "tertiary": 50.0,
    "tertiary_link": 40.0,
    "unclassified": 40.0,
    "residential": 40.0,
    "living_street": 20.0,
    "service": 20.0,
    "road": 50.0,
}

FALLBACK_LANES = {
    "motorway": 3,
    "motorway_link": 1,
    "trunk": 3,
    "trunk_link": 1,
    "primary": 2,
    "primary_link": 1,
    "secondary": 2,
    "secondary_link": 1,
    "tertiary": 1,
    "tertiary_link": 1,
    "unclassified": 1,
    "residential": 1,
    "living_street": 1,
    "service": 1,
    "road": 1,
}

BASE_CAPACITY_BY_CLASS = {
    "motorway": 30,
    "motorway_link": 22,
    "trunk": 30,
    "trunk_link": 22,
    "primary": 24,
    "primary_link": 18,
    "secondary": 24,
    "secondary_link": 18,
    "tertiary": 16,
    "tertiary_link": 14,
    "unclassified": 16,
    "residential": 16,
    "living_street": 8,
    "service": 8,
    "road": 16,
}

IMPLICIT_MAXSPEEDS = {
    "urban": 60.0,
    "rural": 90.0,
    "living_street": 20.0,
    "walk": 10.0,
    "signals": None,
}


@dataclass(slots=True)
class NormalizedRoadAttributes:
    road_class: str
    max_speed_kph: float
    speed_source: str
    lanes: int
    lanes_source: str
    capacity: int
    raw_maxspeed: Any
    raw_lanes: Any


def normalize_road_attributes(attrs: dict[str, Any]) -> NormalizedRoadAttributes:
    road_class = normalize_road_class(attrs.get("highway"))
    max_speed_kph, speed_source = parse_maxspeed(attrs.get("maxspeed"), road_class)
    lanes, lanes_source = parse_lanes(attrs.get("lanes"), road_class)
    capacity = lanes * BASE_CAPACITY_BY_CLASS.get(road_class, BASE_CAPACITY_BY_CLASS["road"])
    return NormalizedRoadAttributes(
        road_class=road_class,
        max_speed_kph=max_speed_kph,
        speed_source=speed_source,
        lanes=lanes,
        lanes_source=lanes_source,
        capacity=max(1, capacity),
        raw_maxspeed=attrs.get("maxspeed"),
        raw_lanes=attrs.get("lanes"),
    )


def normalize_road_class(value: Any) -> str:
    if isinstance(value, (list, tuple, set)):
        value = next(iter(value), "road")
    road_class = str(value or "road").strip().lower()
    return road_class or "road"


def parse_maxspeed(value: Any, road_class: str = "road") -> tuple[float, str]:
    parsed = _parse_numeric_or_implicit(value)
    if parsed is not None:
        return parsed, "osm"
    return FALLBACK_SPEED_KPH.get(road_class, FALLBACK_SPEED_KPH["road"]), "maxspeed_fallback"


def parse_lanes(value: Any, road_class: str = "road") -> tuple[int, str]:
    candidates = _flatten_values(value)
    parsed: list[int] = []
    for candidate in candidates:
        for chunk in re.split(r"[;|,/]", str(candidate)):
            match = re.search(r"\d+", chunk)
            if match:
                parsed.append(max(1, int(match.group(0))))
    if parsed:
        return max(parsed), "osm"
    return FALLBACK_LANES.get(road_class, FALLBACK_LANES["road"]), "lanes_fallback"


def _parse_numeric_or_implicit(value: Any) -> float | None:
    candidates = _flatten_values(value)
    parsed: list[float] = []
    for candidate in candidates:
        raw = str(candidate).strip().lower()
        if not raw:
            continue
        for key, implicit in IMPLICIT_MAXSPEEDS.items():
            if raw.endswith(f":{key}") or raw == key:
                if implicit is not None:
                    parsed.append(implicit)
                break
        else:
            for number in re.findall(r"\d+(?:\.\d+)?", raw):
                speed = float(number)
                if "mph" in raw:
                    speed *= 1.60934
                parsed.append(speed)
    if not parsed:
        return None
    return max(5.0, min(min(parsed), 140.0))


def _flatten_values(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        return [item for item in value if item is not None]
    return [value]
