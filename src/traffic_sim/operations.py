from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path
import re
from typing import Any

from .executive_kpis import build_executive_kpi_block, kpis_by_id
from .run_metadata import build_run_passport, default_limitations, write_run_passport
from .scenario_library import load_scenario_presets
from .traffic_providers import build_provider


FORECAST_HORIZONS_MINUTES = (30, 60, 120)
DEFAULT_BASELINE_ANALYTICS_PATH = Path("data/analytics_normal.json")
DEFAULT_OPERATIONS_DIR = Path("reports/operations")


def generate_operational_playbook(
    incident: dict[str, Any],
    *,
    out_dir: str | Path = DEFAULT_OPERATIONS_DIR,
    baseline_analytics_path: str | Path = DEFAULT_BASELINE_ANALYTICS_PATH,
    root: str | Path = ".",
) -> dict[str, Any]:
    """Create an operator-facing playbook and sibling run passport."""

    normalized = normalize_incident(incident)
    output_dir = Path(out_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    playbook_path = output_dir / f"{normalized['id']}-playbook.json"
    passport_path = output_dir / f"{normalized['id']}-run-passport.json"

    playbook = build_operational_playbook(
        normalized,
        baseline_analytics_path=baseline_analytics_path,
        root=root,
    )
    playbook["outputs"] = {
        "playbookJson": str(playbook_path),
        "runPassportJson": str(passport_path),
    }
    playbook_path.write_text(json.dumps(playbook, indent=2, ensure_ascii=True), encoding="utf-8")
    passport = build_run_passport(
        run_id=normalized["id"],
        scenario_params=normalized,
        seed=_int_or_none(normalized.get("seed")),
        claim_labels={
            "roads": "real-data",
            "traffic": "demo",
            "operations": "proxy",
            "analytics": "proxy",
            "calibration": "proxy",
            "dossier": "proxy",
        },
        data_sources=_operation_data_sources(normalized, baseline_analytics_path),
        limitations=playbook["limitations"],
        root=root,
    )
    write_run_passport(passport, passport_path)
    return playbook


def build_operational_playbook(
    incident: dict[str, Any],
    *,
    baseline_analytics_path: str | Path = DEFAULT_BASELINE_ANALYTICS_PATH,
    root: str | Path = ".",
) -> dict[str, Any]:
    normalized = normalize_incident(incident)
    provider = build_provider(str(normalized["provider"]), normalized.get("providerPath"))
    observations = _incident_observations(provider, normalized)
    provider_status = provider.status()
    severity_score = _severity_score(normalized.get("severity"))
    current_load = _current_load(observations, severity_score)
    current_speed = _current_speed(observations, severity_score)
    missing_data = _missing_data(provider_status, observations)
    affected_corridors = _affected_corridors(normalized)
    forecast = _forecast(
        normalized,
        current_load=current_load,
        current_speed=current_speed,
        severity_score=severity_score,
        has_live_observations=bool(observations),
    )
    baseline = _load_json(baseline_analytics_path)
    incident_analytics = _incident_analytics(baseline, normalized, severity_score, current_load, current_speed)
    kpi_block = build_executive_kpi_block(
        baseline,
        incident_analytics,
        capex_kzt=float(normalized.get("capexKzt", 0) or 0),
        opex_kzt_per_year=float(normalized.get("opexKztPerYear", 10_000_000) or 10_000_000),
        claim_level="proxy",
    )
    actions = _ranked_actions(normalized, forecast, affected_corridors, missing_data)
    limitations = _operation_limitations(missing_data)
    return {
        "id": normalized["id"],
        "kind": "operational-playbook",
        "claimLevel": "proxy",
        "createdAt": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "incident": normalized,
        "decisionSupportNotice": (
            "Operator playbook is decision-support evidence. It does not authorize autonomous traffic control, "
            "road closure, signal retiming, or public communication without human approval."
        ),
        "dataStatus": {
            "provider": provider_status,
            "observationCount": len(observations),
            "observations": [asdict(observation) for observation in observations],
            "missingData": missing_data,
            "claimLevel": "demo" if not observations else "proxy",
        },
        "affectedCorridors": affected_corridors,
        "forecast": forecast,
        "recommendedActions": actions,
        "expectedKpiImpact": {
            "claimLevel": "proxy",
            "summary": _kpi_summary(kpi_block),
            "executiveKpis": kpi_block,
        },
        "operatorChecklist": _operator_checklist(normalized),
        "approvalCaveats": _approval_caveats(normalized, missing_data),
        "limitations": limitations,
        "audit": {
            "runPassport": f"reports/operations/{normalized['id']}-run-passport.json",
            "formulaNote": "Forecast and KPI impacts use transparent proxy formulas until incident feed and observed outcomes are integrated.",
            "claimRule": "No claim is above proxy for operations recommendations in this artifact.",
        },
    }


def normalize_incident(raw: dict[str, Any]) -> dict[str, Any]:
    corridor = str(raw.get("corridor") or raw.get("roadId") or "abay").strip().lower()
    incident_type = str(raw.get("type") or raw.get("incidentType") or "incident").strip().lower()
    incident_id = _safe_id(str(raw.get("id") or f"{corridor}-{incident_type}"))
    road_tags = [str(tag).strip().lower() for tag in raw.get("roadTags", raw.get("road_tags", [])) if str(tag).strip()]
    if corridor and corridor not in road_tags:
        road_tags.insert(0, corridor)
    return {
        "id": incident_id,
        "type": incident_type,
        "corridor": corridor,
        "roadTags": road_tags,
        "severity": str(raw.get("severity") or "major").strip().lower(),
        "startTime": str(raw.get("startTime") or raw.get("start_time") or "17:20"),
        "durationMinutes": max(15, int(float(raw.get("durationMinutes") or raw.get("duration_minutes") or 60))),
        "laneImpact": str(raw.get("laneImpact") or "partial-blockage"),
        "provider": str(raw.get("provider") or raw.get("providerId") or "csv").strip().lower(),
        "providerPath": str(raw.get("providerPath") or "data/traffic_profiles/sample_almaty.csv"),
        "source": str(raw.get("source") or "manual-operator-input"),
        "seed": raw.get("seed", 707),
        "capexKzt": raw.get("capexKzt", 0),
        "opexKztPerYear": raw.get("opexKztPerYear", 10_000_000),
        "notes": str(raw.get("notes") or "Manual incident used for proxy operational playbook generation."),
        "claimLevel": "proxy",
    }


def _incident_observations(provider: Any, incident: dict[str, Any]) -> list[Any]:
    observations = []
    seen = set()
    for road_id in [incident["corridor"], *incident.get("roadTags", [])]:
        for observation in provider.observations_for_road(str(road_id)):
            key = (observation.road_id, observation.time, observation.source)
            if key not in seen:
                observations.append(observation)
                seen.add(key)
    return observations


def _affected_corridors(incident: dict[str, Any]) -> list[dict[str, Any]]:
    tags = {incident["corridor"], *incident.get("roadTags", [])}
    corridors: dict[str, dict[str, Any]] = {}
    try:
        presets = load_scenario_presets()
    except Exception:
        presets = []
    for preset in presets:
        corridor = preset.get("corridor") if isinstance(preset.get("corridor"), dict) else {}
        corridor_id = str(corridor.get("id") or "").lower()
        event_tags = {
            str(tag).lower()
            for event in preset.get("events", [])
            for tag in event.get("road_tags", [])
        }
        if corridor_id in tags or event_tags.intersection(tags):
            corridors[corridor_id or incident["corridor"]] = {
                "id": corridor_id or incident["corridor"],
                "name": corridor.get("name") or (corridor_id or incident["corridor"]).title(),
                "matchingPresetIds": sorted(
                    {
                        *corridors.get(corridor_id or incident["corridor"], {}).get("matchingPresetIds", []),
                        str(preset.get("id")),
                    }
                ),
                "claimLevel": "proxy",
            }
    if not corridors:
        corridors[incident["corridor"]] = {
            "id": incident["corridor"],
            "name": incident["corridor"].replace("_", " ").title(),
            "matchingPresetIds": [],
            "claimLevel": "proxy",
        }
    return list(corridors.values())


def _forecast(
    incident: dict[str, Any],
    *,
    current_load: float,
    current_speed: float,
    severity_score: float,
    has_live_observations: bool,
) -> list[dict[str, Any]]:
    duration = float(incident["durationMinutes"])
    forecasts = []
    for horizon in FORECAST_HORIZONS_MINUTES:
        clearance = min(0.75, horizon / max(duration * 1.5, 1.0))
        load = min(1.35, max(0.05, current_load + severity_score * 0.22 - clearance * 0.28))
        speed = max(6.0, current_speed * (1.0 - severity_score * 0.28 + clearance * 0.18))
        forecasts.append(
            {
                "horizonMinutes": horizon,
                "expectedLoad": round(load, 3),
                "expectedSpeedKph": round(speed, 1),
                "queueRisk": _queue_risk(load),
                "confidence": _confidence(load, horizon, has_live_observations=has_live_observations),
                "claimLevel": "proxy",
                "missingDataFields": [
                    "live incident clearance timestamp",
                    "observed queue length",
                    "downstream signal state",
                ],
            }
        )
    return forecasts


def _ranked_actions(
    incident: dict[str, Any],
    forecast: list[dict[str, Any]],
    affected_corridors: list[dict[str, Any]],
    missing_data: list[str],
) -> list[dict[str, Any]]:
    peak_load = max(float(item["expectedLoad"]) for item in forecast)
    confidence = "medium" if not missing_data and peak_load < 1.0 else "low-medium"
    return [
        {
            "rank": 1,
            "type": "verify_incident",
            "label": "Confirm lane blockage, responder ETA, and safe work zone boundary",
            "rationale": "The playbook must lock the incident facts before detour or signal changes are approved.",
            "affectedCorridors": [item["id"] for item in affected_corridors],
            "confidence": confidence,
            "approvalRequired": "transport duty officer",
            "missingDataFields": missing_data,
            "claimLevel": "proxy",
        },
        {
            "rank": 2,
            "type": "detour_candidate",
            "label": "Prepare managed detour to parallel central corridors",
            "rationale": "Forecast load crosses the queue-risk threshold on the incident corridor.",
            "candidateCorridors": ["Satpaev", "Tole Bi", "Zhambyl"],
            "trigger": {"queueRiskAtOrAbove": "medium", "observedLoadAtOrAbove": 0.85},
            "confidence": "low-medium",
            "approvalRequired": "traffic police and transport duty officer",
            "missingDataFields": ["available police posts", "temporary signage inventory", "public transport detour constraints"],
            "claimLevel": "proxy",
        },
        {
            "rank": 3,
            "type": "signal_phase_candidate",
            "label": "Review temporary green-time bias away from the blocked approach",
            "rationale": "Signal changes can reduce secondary queue spillback, but safety and controller feasibility are not verified.",
            "candidateChange": "temporary -3s to blocked approach / +3s to parallel movement for 30 minutes",
            "confidence": "low",
            "approvalRequired": "signal engineer",
            "missingDataFields": ["controller capability", "pedestrian phase constraints", "bus priority conflicts"],
            "claimLevel": "proxy",
        },
        {
            "rank": 4,
            "type": "public_communications",
            "label": "Draft public advisory for the affected Abay corridor",
            "rationale": "Communication can reduce discretionary demand and supports safe diversion.",
            "channels": ["akimat social channel", "navigation partner notice", "bus operator dispatch"],
            "confidence": "medium",
            "approvalRequired": "communications duty officer",
            "missingDataFields": ["approved message text", "confirmed incident clearance estimate"],
            "claimLevel": "proxy",
        },
    ]


def _operator_checklist(incident: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {"step": 1, "owner": "dispatcher", "action": "Confirm incident source and timestamp.", "required": True},
        {"step": 2, "owner": "traffic engineer", "action": "Check detector/camera evidence before changing signal plans.", "required": True},
        {"step": 3, "owner": "field team", "action": "Confirm detour signs and traffic police availability.", "required": True},
        {"step": 4, "owner": "bus operations", "action": f"Notify routes crossing {incident['corridor'].title()}.", "required": False},
        {"step": 5, "owner": "communications", "action": "Publish advisory only after duty-officer approval.", "required": True},
    ]


def _incident_analytics(
    baseline: dict[str, Any],
    incident: dict[str, Any],
    severity_score: float,
    current_load: float,
    current_speed: float,
) -> dict[str, Any]:
    payload = json.loads(json.dumps(baseline))
    summary = payload.setdefault("summary", {})
    baseline_trip = float(summary.get("average_trip_time_seconds", 1800.0) or 1800.0)
    baseline_congestion = float(summary.get("congestion_index", 50.0) or 50.0)
    summary["average_trip_time_seconds"] = round(baseline_trip * (1.0 + severity_score * 0.26 + current_load * 0.08), 2)
    summary["congestion_index"] = round(min(100.0, baseline_congestion + severity_score * 22.0 + current_load * 8.0), 2)
    series = payload.get("time_series") or []
    if isinstance(series, list) and series:
        for item in series:
            if isinstance(item, dict):
                item["congestion_index"] = round(min(100.0, float(item.get("congestion_index", baseline_congestion)) + severity_score * 12.0), 2)
                item["avg_speed_kph"] = round(max(6.0, min(float(item.get("avg_speed_kph", current_speed)), current_speed)), 1)
    payload["operationIncident"] = incident["id"]
    return payload


def _kpi_summary(kpi_block: dict[str, Any]) -> dict[str, Any]:
    by_id = kpis_by_id(kpi_block)
    return {
        "personHoursDelta": by_id.get("person_hours", {}).get("delta"),
        "speedDeltaKph": by_id.get("corridor_speed_delta", {}).get("delta"),
        "queueLoadDelta": by_id.get("queue_load_proxy", {}).get("delta"),
        "busReliabilityDelta": by_id.get("bus_reliability_proxy", {}).get("delta"),
        "co2DeltaKg": by_id.get("co2_proxy", {}).get("delta"),
        "roiProxy": by_id.get("roi_proxy", {}).get("measure"),
        "confidence": kpi_block.get("confidence"),
    }


def _approval_caveats(incident: dict[str, Any], missing_data: list[str]) -> list[str]:
    caveats = [
        "Human approval is required for any detour, signal phase change, public advisory, or field deployment.",
        "Recommended actions are ranked decision-support candidates, not automatic control instructions.",
        "Police, emergency access, pedestrian safety, and public transport constraints must be checked before field action.",
    ]
    if missing_data:
        caveats.append(f"Missing data before higher-confidence action: {', '.join(missing_data)}.")
    if incident["claimLevel"] != "real-data":
        caveats.append("Incident input is not linked to a verified live municipal incident feed.")
    return caveats


def _operation_limitations(missing_data: list[str]) -> list[str]:
    limitations = [
        "30/60/120 minute forecasts are deterministic proxies; they are not live traffic predictions.",
        "Detour and signal candidates require engineer validation and field authority approval.",
        "No legal, emergency-service, or construction-permit constraints are automatically checked.",
        *default_limitations(),
    ]
    if missing_data:
        limitations.append(f"Operational confidence is limited by missing fields: {', '.join(missing_data)}.")
    return limitations


def _operation_data_sources(incident: dict[str, Any], baseline_analytics_path: str | Path) -> list[dict[str, Any]]:
    return [
        {
            "id": "manual-incident",
            "label": "Manual incident input",
            "path": "data/operations/sample_incident_abay.json",
            "claim_label": "proxy",
            "source_type": incident["source"],
            "freshness": "generated for G007 operational playbook",
            "notes": "Manual incident input; replace with approved municipal feed for real-data claims.",
        },
        {
            "id": "traffic-profile-csv",
            "label": "Sample Almaty traffic profile",
            "path": incident["providerPath"],
            "claim_label": "demo",
            "source_type": "local CSV traffic profile",
            "freshness": "local file snapshot",
            "notes": "Used only for proxy operational load context.",
        },
        {
            "id": "scenario-library",
            "label": "Municipal scenario library",
            "path": "data/scenarios/library/municipal_presets.json",
            "claim_label": "proxy",
            "source_type": "structured scenario presets",
            "freshness": "G006 local artifact",
            "notes": "Used to match affected corridor and action types.",
        },
        {
            "id": "baseline-analytics",
            "label": "Baseline analytics for KPI impact",
            "path": str(baseline_analytics_path),
            "claim_label": "proxy",
            "source_type": "generated proxy analytics",
            "freshness": "local generated artifact",
            "notes": "Used for transparent KPI impact deltas.",
        },
    ]


def _missing_data(provider_status: dict[str, Any], observations: list[Any]) -> list[str]:
    missing = []
    if not provider_status.get("available"):
        missing.append("available traffic provider")
    if not observations:
        missing.append("corridor traffic observations")
    missing.extend(["verified incident clearance estimate", "observed queue length", "signal controller state"])
    return missing


def _current_load(observations: list[Any], severity_score: float) -> float:
    if observations:
        return min(1.2, max(float(observation.load) for observation in observations))
    return min(1.15, 0.55 + severity_score * 0.42)


def _current_speed(observations: list[Any], severity_score: float) -> float:
    if observations:
        return max(6.0, min(float(observation.speed_kph) for observation in observations))
    return max(8.0, 42.0 - severity_score * 24.0)


def _severity_score(value: Any) -> float:
    if isinstance(value, (int, float)):
        return max(0.0, min(1.0, float(value)))
    label = str(value or "moderate").lower()
    return {
        "minor": 0.25,
        "moderate": 0.45,
        "major": 0.7,
        "severe": 0.9,
        "critical": 1.0,
    }.get(label, 0.55)


def _queue_risk(load: float) -> str:
    if load >= 1.0:
        return "high"
    if load >= 0.82:
        return "medium"
    return "low"


def _confidence(load: float, horizon: int, *, has_live_observations: bool) -> dict[str, Any]:
    score = 0.45 if has_live_observations else 0.34
    score -= 0.04 if horizon == 120 else 0.0
    score -= 0.05 if load >= 1.0 else 0.0
    return {
        "level": "low-medium" if score >= 0.35 else "low",
        "score": round(max(0.1, score), 2),
        "claimLevel": "proxy",
    }


def _load_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _safe_id(value: str) -> str:
    safe = re.sub(r"[^a-zA-Z0-9_-]+", "-", value.strip().lower()).strip("-")
    return safe or "operation-incident"


def _int_or_none(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
