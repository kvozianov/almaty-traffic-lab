from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any

from .network import CityGraph
from .time_profiles import format_hhmm, parse_hhmm


@dataclass(slots=True)
class ScenarioEvent:
    event_id: str
    type: str
    road_id: str | None = None
    start_time: str = "17:10"
    duration_minutes: int = 40
    enabled: bool = True
    capacity_factor: float = 0.35
    speed_factor: float = 0.45
    signal_delay_s: float = 60.0
    intensity: float = 1.0

    @property
    def end_time(self) -> str:
        return format_hhmm(parse_hhmm(self.start_time) + self.duration_minutes)

    def active_at(self, minute_of_day: int) -> bool:
        if not self.enabled:
            return False
        return is_window_active(self.start_time, self.duration_minutes, minute_of_day)

    def to_payload(self, active: bool | None = None) -> dict[str, object]:
        return {
            "id": self.event_id,
            "type": self.type,
            "roadId": self.road_id,
            "startTime": self.start_time,
            "durationMinutes": self.duration_minutes,
            "endTime": self.end_time,
            "enabled": self.enabled,
            "capacityFactor": self.capacity_factor,
            "speedFactor": self.speed_factor,
            "signalDelayS": self.signal_delay_s,
            "intensity": self.intensity,
            "active": active,
        }


def is_window_active(start_time: str, duration_minutes: int, minute_of_day: int) -> bool:
    start = parse_hhmm(start_time)
    duration = max(1, int(duration_minutes))
    offset = (minute_of_day - start) % (24 * 60)
    return 0 <= offset < duration


def normalize_events(raw_events: list[Any] | None) -> list[ScenarioEvent]:
    events: list[ScenarioEvent] = []
    for index, raw in enumerate(raw_events or []):
        if hasattr(raw, "model_dump"):
            item = raw.model_dump()
        elif isinstance(raw, dict):
            item = raw
        else:
            continue
        event_type = str(item.get("type", "accident"))
        if event_type == "none":
            continue
        events.append(
            ScenarioEvent(
                event_id=str(item.get("id") or item.get("event_id") or f"event-{index + 1}"),
                type=event_type,
                road_id=item.get("road_id") or item.get("roadId"),
                start_time=str(item.get("start_time") or item.get("startTime") or "17:10"),
                duration_minutes=int(item.get("duration_minutes") or item.get("durationMinutes") or 40),
                enabled=bool(item.get("enabled", True)),
                capacity_factor=float(item.get("capacity_factor") or item.get("capacityFactor") or 0.35),
                speed_factor=float(item.get("speed_factor") or item.get("speedFactor") or 0.45),
                signal_delay_s=float(item.get("signal_delay_s") or item.get("signalDelayS") or 60.0),
                intensity=float(item.get("intensity", 1.0)),
            )
        )
    return events


def default_timeline_events(selected_road_id: str | None = None) -> list[ScenarioEvent]:
    return [
        ScenarioEvent("preset-accident-1710", "accident", selected_road_id, "17:10", 35, True, 0.35, 0.4),
        ScenarioEvent("preset-repair-1740", "repair", selected_road_id, "17:40", 40, True, 0.0, 0.2),
        ScenarioEvent("preset-weather-1800", "weather", None, "18:00", 45, True, 0.75, 0.72),
    ]


def generate_random_events(graph: CityGraph, seed: int, duration_minutes: int, start_time: str = "17:00") -> list[ScenarioEvent]:
    rng = random.Random(seed + 9091)
    roads = [road for road in graph.roads.values() if road.is_open]
    roads.sort(key=lambda road: (road.length_m, road.capacity), reverse=True)
    if not roads:
        return []
    event_count = max(1, min(5, duration_minutes // 45 + 1))
    events: list[ScenarioEvent] = []
    event_types = ["accident", "repair", "closure", "weather", "capacity_reduction"]
    start_minute = parse_hhmm(start_time)
    for index in range(event_count):
        road = rng.choice(roads[: min(len(roads), 160)])
        event_type = rng.choice(event_types)
        minute = start_minute + rng.randint(5, max(8, duration_minutes))
        duration = rng.randint(18, 70)
        events.append(
            ScenarioEvent(
                event_id=f"random-{index + 1}",
                type=event_type,
                road_id=None if event_type == "weather" else road.road_id,
                start_time=format_hhmm(minute),
                duration_minutes=duration,
                capacity_factor=rng.uniform(0.15, 0.65),
                speed_factor=rng.uniform(0.25, 0.75),
                signal_delay_s=rng.uniform(35, 95),
            )
        )
    return events


def attach_timeline_metadata(graph: CityGraph, events: list[ScenarioEvent]) -> list[str]:
    affected: set[str] = set()
    for event in events:
        target_roads = _target_roads(graph, event)
        for road_id in target_roads:
            road = graph.roads[road_id]
            timeline_events = list(road.metadata.get("timeline_events", []))
            timeline_events.append(event.to_payload())
            road.metadata["timeline_events"] = timeline_events
            affected.add(road_id)
    return sorted(affected)


def active_events(events: list[ScenarioEvent], minute_of_day: int) -> list[ScenarioEvent]:
    return [event for event in events if event.active_at(minute_of_day)]


def apply_active_events(graph: CityGraph, events: list[ScenarioEvent], minute_of_day: int) -> list[str]:
    affected: set[str] = set()
    for event in active_events(events, minute_of_day):
        for road_id in _target_roads(graph, event):
            road = graph.roads[road_id]
            affected.add(road_id)
            if event.type == "accident":
                road.capacity_modifier *= event.capacity_factor
                road.speed_modifier *= event.speed_factor
                road.metadata["scenario"] = "timeline accident"
            elif event.type == "repair":
                road.is_open = False
                road.metadata["scenario"] = "timeline repair"
            elif event.type == "closure":
                road.is_open = False
                road.metadata["scenario"] = "timeline closure"
            elif event.type == "capacity_reduction":
                road.capacity_modifier *= event.capacity_factor
                road.metadata["scenario"] = "timeline capacity"
            elif event.type == "signal":
                road.signal_delay_s += event.signal_delay_s
                road.metadata["scenario"] = "timeline signal"
            elif event.type == "weather":
                road.speed_modifier *= event.speed_factor
                road.metadata["scenario"] = "timeline weather"
    return sorted(affected)


def events_payload(events: list[ScenarioEvent], minute_of_day: int | None = None) -> list[dict[str, object]]:
    return [event.to_payload(event.active_at(minute_of_day) if minute_of_day is not None else None) for event in events]


def _target_roads(graph: CityGraph, event: ScenarioEvent) -> list[str]:
    if event.type == "weather":
        return list(graph.roads)[: max(25, min(len(graph.roads), 250))]
    if event.road_id in graph.roads:
        return [str(event.road_id)]
    if not graph.roads:
        return []
    return [max(graph.roads, key=lambda road_id: graph.roads[road_id].length_m)]
