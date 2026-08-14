from __future__ import annotations

from pathlib import Path
import json
from typing import Any

from .network import CityGraph
from .run_metadata import CLAIM_LABELS
from .timeline import ScenarioEvent, apply_active_events, attach_timeline_metadata, normalize_events


DEFAULT_LIBRARY_PATH = Path("data/scenarios/almaty_report_scenarios.json")
REQUIRED_MODEL_EFFECTS = ("graph", "demand", "signal", "speed", "capacity", "cost", "risk")


def load_scenario_presets(path: str | Path = DEFAULT_LIBRARY_PATH) -> list[dict[str, Any]]:
    payload = _load_json(path)
    if payload.get("source"):
        source = Path(str(payload["source"]))
        if not source.exists():
            source = Path(path).parent / source
        return load_scenario_presets(source)
    presets = payload.get("presets")
    if not isinstance(presets, list):
        raise ValueError("Scenario library must include a presets array.")
    normalized = [_normalize_preset(item) for item in presets if isinstance(item, dict)]
    if len(normalized) < 10:
        raise ValueError("G006 requires at least 10 municipal scenario presets.")
    return normalized


def get_scenario_preset(preset_id: str, path: str | Path = DEFAULT_LIBRARY_PATH) -> dict[str, Any]:
    for preset in load_scenario_presets(path):
        if preset["id"] == preset_id:
            return preset
    raise KeyError(f"Unknown scenario preset: {preset_id}")


def events_for_preset(preset_id: str, path: str | Path = DEFAULT_LIBRARY_PATH) -> list[ScenarioEvent]:
    preset = get_scenario_preset(preset_id, path)
    return normalize_events(preset.get("events", []))


def apply_scenario_preset(
    graph: CityGraph,
    preset_id: str,
    *,
    minute_of_day: int,
    path: str | Path = DEFAULT_LIBRARY_PATH,
) -> dict[str, Any]:
    preset = get_scenario_preset(preset_id, path)
    events = normalize_events(preset.get("events", []))
    timeline_roads = attach_timeline_metadata(graph, events)
    active_roads = apply_active_events(graph, events, minute_of_day)
    return {
        "preset": preset,
        "timelineRoads": timeline_roads,
        "activeRoads": active_roads,
        "eventCount": len(events),
        "dossierCompatible": bool(preset.get("dossierCompatible")),
    }


def _normalize_preset(raw: dict[str, Any]) -> dict[str, Any]:
    claim_level = _claim_level(raw.get("claimLevel", "proxy"))
    model_effects = raw.get("modelEffects")
    if not isinstance(model_effects, dict):
        raise ValueError(f"Scenario preset {raw.get('id')} must include modelEffects.")
    missing_effects = [key for key in REQUIRED_MODEL_EFFECTS if key not in model_effects]
    if missing_effects:
        raise ValueError(f"Scenario preset {raw.get('id')} is missing modelEffects keys: {missing_effects}")
    events = raw.get("events")
    if not isinstance(events, list) or not events:
        raise ValueError(f"Scenario preset {raw.get('id')} must include at least one event.")
    costs = raw.get("costs")
    if not isinstance(costs, dict) or "capexKzt" not in costs or "opexKztPerYear" not in costs:
        raise ValueError(f"Scenario preset {raw.get('id')} must include CAPEX/OPEX placeholders.")
    preset = dict(raw)
    preset["claimLevel"] = claim_level
    preset["dossierCompatible"] = bool(raw.get("dossierCompatible", True))
    preset["events"] = [_normalize_event(event) for event in events if isinstance(event, dict)]
    preset["assumptions"] = [str(item) for item in raw.get("assumptions", [])]
    preset["risks"] = [str(item) for item in raw.get("risks", [])]
    preset["targetKpis"] = [str(item) for item in raw.get("targetKpis", [])]
    return preset


def _normalize_event(raw: dict[str, Any]) -> dict[str, Any]:
    event = dict(raw)
    event.setdefault("enabled", True)
    event.setdefault("start_time", "17:00")
    event.setdefault("duration_minutes", 60)
    event.setdefault("capacity_factor", 1.0)
    event.setdefault("speed_factor", 1.0)
    event.setdefault("signal_delay_s", 0.0)
    event.setdefault("intensity", 1.0)
    event["road_tags"] = [str(tag) for tag in event.get("road_tags", [])]
    return event


def _claim_level(value: Any) -> str:
    label = str(value)
    if label not in CLAIM_LABELS:
        raise ValueError(f"Unsupported claim label: {label}. Expected one of {sorted(CLAIM_LABELS)}")
    return label


def _load_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))
