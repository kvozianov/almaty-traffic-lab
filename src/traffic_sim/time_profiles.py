from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .models import Road


DEFAULT_PROFILE_PATH = Path("data/time_profiles/almaty_weekday.json")


@dataclass(slots=True)
class TimeProfile:
    profile_id: str
    name: str
    default_speed_multiplier: float
    periods: list[dict[str, Any]]
    corridors: dict[str, dict[str, Any]]

    def speed_multiplier_for_road(self, road: Road, minute_of_day: int) -> float:
        multiplier = self.default_speed_multiplier
        for period in self.periods:
            if _contains_minute(period["start"], period["end"], minute_of_day):
                multiplier *= float(period.get("speed_multiplier", 1.0))
        road_name = str(road.metadata.get("name") or road.road_id).lower()
        for corridor_id, corridor in self.corridors.items():
            aliases = [corridor_id, *corridor.get("aliases", [])]
            if any(alias.lower() in road_name for alias in aliases):
                for period in corridor.get("periods", []):
                    if _contains_minute(period["start"], period["end"], minute_of_day):
                        multiplier *= float(period.get("speed_multiplier", 1.0))
        return max(0.15, min(multiplier, 1.5))

    def demand_multiplier(self, minute_of_day: int) -> float:
        multiplier = 1.0
        for period in self.periods:
            if _contains_minute(period["start"], period["end"], minute_of_day):
                multiplier *= float(period.get("demand_multiplier", 1.0))
        return max(0.2, min(multiplier, 3.0))


def load_time_profile(path: str | Path = DEFAULT_PROFILE_PATH) -> TimeProfile:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return TimeProfile(
        profile_id=payload["id"],
        name=payload["name"],
        default_speed_multiplier=float(payload.get("default_speed_multiplier", 1.0)),
        periods=list(payload.get("periods", [])),
        corridors=dict(payload.get("corridors", {})),
    )


def list_time_profiles() -> list[dict[str, str]]:
    return [{"id": "almaty_weekday", "name": "Almaty weekday"}]


def parse_hhmm(value: str) -> int:
    hours, minutes = value.split(":", 1)
    return (int(hours) % 24) * 60 + int(minutes)


def format_hhmm(minute_of_day: int) -> str:
    minute_of_day %= 24 * 60
    return f"{minute_of_day // 60:02d}:{minute_of_day % 60:02d}"


def _contains_minute(start: str, end: str, minute_of_day: int) -> bool:
    start_minute = parse_hhmm(start)
    end_minute = parse_hhmm(end)
    minute_of_day %= 24 * 60
    if start_minute <= end_minute:
        return start_minute <= minute_of_day <= end_minute
    return minute_of_day >= start_minute or minute_of_day <= end_minute
