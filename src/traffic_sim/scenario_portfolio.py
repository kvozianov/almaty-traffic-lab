from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from pathlib import Path
import csv
import json
from typing import Any

from .executive_kpis import build_executive_kpi_block, kpis_by_id
from .run_metadata import CLAIM_LABELS, build_run_passport, write_run_passport


MATRIX_KPI_IDS = [
    "person_hours_saved",
    "corridor_speed_delta",
    "queue_load_proxy",
    "bus_reliability_proxy",
    "co2_proxy",
    "nox_proxy",
    "capex_placeholder",
    "opex_placeholder",
    "annual_time_savings_proxy",
    "roi_proxy",
    "payback_proxy",
]


@dataclass(frozen=True, slots=True)
class ScenarioMeasure:
    id: str
    name: str
    type: str
    corridor: dict[str, Any]
    geometry_refs: list[str] = field(default_factory=list)
    scenario_params: dict[str, Any] = field(default_factory=dict)
    costs: dict[str, Any] = field(default_factory=dict)
    constraints: list[str] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    target_kpis: list[str] = field(default_factory=list)
    proxy_effects: dict[str, float] = field(default_factory=dict)
    claim_level: str = "proxy"


@dataclass(frozen=True, slots=True)
class ScenarioPortfolio:
    id: str
    title: str
    baseline: dict[str, Any]
    measures: list[ScenarioMeasure]
    seed: int = 7
    claim_level: str = "proxy"
    limitations: list[str] = field(default_factory=list)


def load_portfolio(path: str | Path) -> ScenarioPortfolio:
    payload = _load_json(path)
    claim_level = _claim_level(payload.get("claimLevel", "proxy"))
    measures = [_measure_from_payload(item) for item in payload.get("measures", [])]
    if len(measures) < 3:
        raise ValueError("ScenarioPortfolio must include at least three measures for G003.")
    baseline = payload.get("baseline")
    if not isinstance(baseline, dict) or not baseline.get("analyticsPath"):
        raise ValueError("ScenarioPortfolio baseline.analyticsPath is required.")
    return ScenarioPortfolio(
        id=str(payload["id"]),
        title=str(payload.get("title", payload["id"])),
        seed=int(payload.get("seed", 7)),
        claim_level=claim_level,
        baseline=baseline,
        measures=measures,
        limitations=[str(item) for item in payload.get("limitations", [])],
    )


def run_portfolio(config_path: str | Path, out_dir: str | Path | None = None) -> dict[str, Any]:
    config_path = Path(config_path)
    portfolio = load_portfolio(config_path)
    output_dir = Path(out_dir or f"reports/portfolio/{portfolio.id}")
    analytics_dir = output_dir / "analytics"
    passports_dir = output_dir / "run-passports"
    output_dir.mkdir(parents=True, exist_ok=True)
    analytics_dir.mkdir(parents=True, exist_ok=True)
    passports_dir.mkdir(parents=True, exist_ok=True)

    baseline_path = Path(str(portfolio.baseline["analyticsPath"]))
    if not baseline_path.exists():
        raise FileNotFoundError(f"Portfolio baseline analytics not found: {baseline_path}")
    baseline_analytics = _load_json(baseline_path)
    baseline_summary = baseline_analytics.get("summary", {})

    measure_results = []
    matrix_rows = []
    for measure in portfolio.measures:
        analytics = _analytics_for_measure(baseline_analytics, measure)
        analytics_path = analytics_dir / f"{measure.id}.json"
        _write_json(analytics_path, analytics)

        passport = build_run_passport(
            run_id=f"{portfolio.id}:{measure.id}",
            scenario_params={
                "portfolioId": portfolio.id,
                "portfolioTitle": portfolio.title,
                "baseline": portfolio.baseline,
                "measure": {
                    "id": measure.id,
                    "name": measure.name,
                    "type": measure.type,
                    "corridor": measure.corridor,
                    "geometryRefs": measure.geometry_refs,
                    "scenarioParams": measure.scenario_params,
                    "constraints": measure.constraints,
                    "assumptions": measure.assumptions,
                    "targetKpis": measure.target_kpis,
                    "proxyEffects": measure.proxy_effects,
                },
            },
            seed=portfolio.seed,
            claim_labels={
                "roads": "real-data",
                "traffic": "demo",
                "analytics": "proxy",
                "calibration": "proxy",
                "dossier": "proxy",
                "portfolio": portfolio.claim_level,
            },
            data_sources=[
                {
                    "id": "portfolio-config",
                    "label": "Scenario portfolio config",
                    "path": str(config_path),
                    "claim_label": portfolio.claim_level,
                    "source_type": "structured municipal proxy scenario config",
                    "freshness": "local workspace snapshot",
                    "notes": "Defines the shared baseline, measures, costs, constraints, assumptions, and proxy effects.",
                },
                {
                    "id": "baseline-analytics",
                    "label": "Shared baseline analytics",
                    "path": str(baseline_path),
                    "claim_label": "proxy",
                    "source_type": "generated proxy analytics",
                    "freshness": "local workspace snapshot",
                    "notes": "Common baseline used for every portfolio measure.",
                },
                {
                    "id": "measure-analytics",
                    "label": f"{measure.name} analytics",
                    "path": str(analytics_path),
                    "claim_label": measure.claim_level,
                    "source_type": "portfolio proxy analytics",
                    "freshness": "generated locally by ScenarioPortfolio runner",
                    "notes": "Derived from the common baseline with explicit proxyEffects.",
                },
                {
                    "id": "corridor-pack-abay",
                    "label": "First Corridor Pack - Abay",
                    "path": "docs/obsidian/03-registries/First Corridor Pack - Abay.md",
                    "claim_label": "proxy",
                    "source_type": "Obsidian corridor anchor",
                    "freshness": "2026-06-05 workbench note",
                    "notes": "Keeps first portfolio measures anchored to the first corridor pack.",
                },
            ],
            limitations=portfolio.limitations or None,
        )
        passport_path = passports_dir / f"{measure.id}-run-passport.json"
        write_run_passport(passport, passport_path)

        row = _matrix_row(portfolio, measure, analytics, analytics_path, passport_path)
        matrix_rows.append(row)
        measure_results.append(
            {
                "id": measure.id,
                "name": measure.name,
                "type": measure.type,
                "corridor": measure.corridor,
                "geometryRefs": measure.geometry_refs,
                "scenarioParams": measure.scenario_params,
                "constraints": measure.constraints,
                "assumptions": measure.assumptions,
                "targetKpis": measure.target_kpis,
                "proxyEffects": measure.proxy_effects,
                "claimLevel": measure.claim_level,
                "costs": measure.costs,
                "analyticsPath": str(analytics_path),
                "runPassportPath": str(passport_path),
                "executiveKpis": analytics["executive_kpis"],
                "decisionSupport": _decision_support(analytics["executive_kpis"]),
            }
        )

    matrix_rows.sort(key=_rank_key, reverse=True)
    for rank, row in enumerate(matrix_rows, start=1):
        row["rank"] = rank

    result = {
        "id": portfolio.id,
        "title": portfolio.title,
        "claimLevel": portfolio.claim_level,
        "seed": portfolio.seed,
        "baseline": {
            "label": portfolio.baseline.get("label", "Baseline"),
            "analyticsPath": str(baseline_path),
            "summary": baseline_summary,
        },
        "measures": measure_results,
        "matrix": matrix_rows,
        "limitations": portfolio.limitations,
        "outputs": {},
    }

    result_path = output_dir / "portfolio_results.json"
    matrix_path = output_dir / "kpi_matrix.csv"
    _write_json(result_path, result)
    _write_matrix_csv(matrix_path, matrix_rows)
    result["outputs"] = {"json": str(result_path), "csv": str(matrix_path)}
    _write_json(result_path, result)
    return result


def _measure_from_payload(payload: dict[str, Any]) -> ScenarioMeasure:
    claim_level = _claim_level(payload.get("claimLevel", "proxy"))
    costs = payload.get("costs") if isinstance(payload.get("costs"), dict) else {}
    return ScenarioMeasure(
        id=str(payload["id"]),
        name=str(payload.get("name", payload["id"])),
        type=str(payload["type"]),
        corridor=dict(payload.get("corridor", {})),
        geometry_refs=[str(item) for item in payload.get("geometryRefs", [])],
        scenario_params=dict(payload.get("scenarioParams", {})),
        costs=costs,
        constraints=[str(item) for item in payload.get("constraints", [])],
        assumptions=[str(item) for item in payload.get("assumptions", [])],
        target_kpis=[str(item) for item in payload.get("targetKpis", [])],
        proxy_effects={str(key): float(value) for key, value in dict(payload.get("proxyEffects", {})).items()},
        claim_level=claim_level,
    )


def _analytics_for_measure(baseline: dict[str, Any], measure: ScenarioMeasure) -> dict[str, Any]:
    analytics = deepcopy(baseline)
    effects = measure.proxy_effects
    summary = analytics.setdefault("summary", {})
    trip_factor = effects.get("tripTimeFactor", 1.0)
    trip_delta = effects.get("tripTimeDeltaSeconds", 0.0)
    congestion_delta = effects.get("congestionDelta", 0.0)
    congestion_factor = effects.get("congestionFactor", 1.0)
    vehicle_factor = effects.get("vehicleFactor", 1.0)
    speed_delta = effects.get("speedDeltaKph", 0.0)
    speed_factor = effects.get("speedFactor", 1.0)

    summary["average_trip_time_seconds"] = _round(max(60.0, _num(summary.get("average_trip_time_seconds")) * trip_factor + trip_delta))
    summary["congestion_index"] = _round(_clamp(_num(summary.get("congestion_index")) * congestion_factor + congestion_delta, 0.0, 100.0))
    summary["total_active_vehicles"] = int(max(1, round(_num(summary.get("total_active_vehicles")) * vehicle_factor)))

    for entry in analytics.get("time_series", []):
        if not isinstance(entry, dict):
            continue
        entry["congestion_index"] = _round(_clamp(_num(entry.get("congestion_index")) * congestion_factor + congestion_delta, 0.0, 100.0))
        entry["avg_speed_kph"] = _round(_clamp(_num(entry.get("avg_speed_kph")) * speed_factor + speed_delta, 5.0, 95.0))

    for forecast in analytics.get("ml_forecast", []):
        if not isinstance(forecast, dict):
            continue
        forecast["predicted_congestion"] = _round(_clamp(_num(forecast.get("predicted_congestion")) * congestion_factor + congestion_delta, 0.0, 100.0))

    analytics["scenario"] = {
        "id": measure.id,
        "name": measure.name,
        "type": measure.type,
        "corridor": measure.corridor,
        "proxyEffects": effects,
        "claimLevel": measure.claim_level,
    }
    analytics["executive_kpis"] = build_executive_kpi_block(
        baseline,
        analytics,
        capex_kzt=_optional_num(measure.costs.get("capexKzt")),
        opex_kzt_per_year=_optional_num(measure.costs.get("opexKztPerYear")),
        claim_level=measure.claim_level,
    )
    return analytics


def _matrix_row(
    portfolio: ScenarioPortfolio,
    measure: ScenarioMeasure,
    analytics: dict[str, Any],
    analytics_path: Path,
    passport_path: Path,
) -> dict[str, Any]:
    by_id = kpis_by_id(analytics["executive_kpis"])
    row: dict[str, Any] = {
        "rank": 0,
        "portfolio_id": portfolio.id,
        "scenario_id": measure.id,
        "scenario_name": measure.name,
        "scenario_type": measure.type,
        "corridor_id": measure.corridor.get("id", ""),
        "claim_level": measure.claim_level,
        "analytics_path": str(analytics_path),
        "run_passport_path": str(passport_path),
        "decision_signal": _decision_support(analytics["executive_kpis"])["signal"],
    }
    for kpi_id in MATRIX_KPI_IDS:
        kpi = by_id.get(kpi_id, {})
        if kpi_id in {"person_hours_saved", "annual_time_savings_proxy", "roi_proxy", "payback_proxy"}:
            value = kpi.get("measure")
        else:
            value = kpi.get("delta")
        row[kpi_id] = value
    return row


def _decision_support(executive_kpis: dict[str, Any]) -> dict[str, Any]:
    by_id = kpis_by_id(executive_kpis)
    person_hours_saved = _num(by_id.get("person_hours_saved", {}).get("measure"))
    roi = _num(by_id.get("roi_proxy", {}).get("measure"))
    payback_available = bool(by_id.get("payback_proxy", {}).get("available", False))
    if person_hours_saved <= 0:
        signal = "defer_or_reject"
        rationale = "Proxy KPI block does not show person-hour savings."
    elif roi > 0 and payback_available:
        signal = "candidate_for_dossier"
        rationale = "Proxy KPI block shows positive person-hour savings and positive ROI placeholder."
    else:
        signal = "request_more_evidence"
        rationale = "Proxy benefit is positive, but cost-sensitive ROI/payback remain weak."
    return {"signal": signal, "rationale": rationale, "claimLevel": executive_kpis.get("claimLevel", "proxy")}


def _rank_key(row: dict[str, Any]) -> tuple[float, float]:
    return (_num(row.get("person_hours_saved")), _num(row.get("roi_proxy")))


def _write_matrix_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = [
        "rank",
        "portfolio_id",
        "scenario_id",
        "scenario_name",
        "scenario_type",
        "corridor_id",
        "claim_level",
        "decision_signal",
        *MATRIX_KPI_IDS,
        "analytics_path",
        "run_passport_path",
    ]
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key) for key in fieldnames})


def _load_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _write_json(path: str | Path, payload: dict[str, Any]) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")


def _claim_level(value: Any) -> str:
    label = str(value)
    if label not in CLAIM_LABELS:
        raise ValueError(f"Unsupported claim label: {label}. Expected one of {sorted(CLAIM_LABELS)}")
    return label


def _optional_num(value: Any) -> float | None:
    if value is None:
        return None
    return _num(value)


def _num(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _clamp(value: float, low: float, high: float) -> float:
    return min(high, max(low, value))


def _round(value: float) -> float:
    return round(value, 3)
