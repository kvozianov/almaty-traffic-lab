from __future__ import annotations

from pathlib import Path
import csv
import html
import json
import math
import re
from typing import Any

from .contracts import canonical_json, validate_claim_level, validate_paired_experiment_result
from .executive_kpis import build_executive_kpi_block, kpis_by_id
from .run_metadata import build_run_passport, write_run_passport


PRIMARY_KPI_RULES: tuple[tuple[str, str, float], ...] = (
    ("person_hours", "lower_is_better", 0.001),
    ("corridor_speed_delta", "higher_is_better", 0.001),
    ("queue_load_proxy", "lower_is_better", 0.001),
    ("bus_reliability_proxy", "higher_is_better", 0.001),
    ("co2_proxy", "lower_is_better", 0.001),
    ("nox_proxy", "lower_is_better", 0.001),
)
ECONOMIC_KPI_IDS = (
    "capex_placeholder",
    "opex_placeholder",
    "annual_time_savings_proxy",
    "roi_proxy",
    "payback_proxy",
)
_RUN_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


def generate_scenario_dossier(
    config_path: str | Path | dict[str, Any],
    *,
    output_dir: str | Path | None = None,
    run_passport_path: str | Path | None = None,
    release_run_id: str | None = None,
    paired_experiment_schema_path: str | Path | None = None,
) -> dict[str, Any]:
    config = dict(config_path) if isinstance(config_path, dict) else _load_json(config_path)
    _validate_dossier_config(config)
    audit_run_id = _resolve_audit_run_id(config, release_run_id=release_run_id)
    baseline = _load_json(config["baseline"]["analyticsPath"])
    measure = _load_json(config["measure"]["analyticsPath"])
    paired_result = _load_and_verify_pair(
        config,
        baseline=baseline,
        measure=measure,
        schema_path=paired_experiment_schema_path,
    )
    claim_level = validate_claim_level(str(config.get("claimLevel", "proxy")))
    costs = config.get("costs", {})
    executive_kpis = build_executive_kpi_block(
        baseline,
        measure,
        capex_kzt=costs.get("capexKzt"),
        opex_kzt_per_year=costs.get("opexKztPerYear"),
        capex_placeholder=costs.get("capexPlaceholder", True),
        opex_placeholder=costs.get("opexPlaceholder", True),
        roi_payback_placeholder=costs.get("roiPaybackPlaceholder", True),
        claim_level=claim_level,
    )
    recommendation = build_recommendation(executive_kpis, claim_level=claim_level)
    run_passport = build_run_passport(
        run_id=audit_run_id,
        scenario_params={
            "corridor": config.get("corridor"),
            "baseline": config.get("baseline", {}).get("scenario", {}),
            "measure": config.get("measure", {}).get("scenario", {}),
            "decisionQuestion": config.get("decisionQuestion"),
        },
        seed=int(config.get("seed", 7)),
        data_sources=config.get("dataSources") if isinstance(config.get("dataSources"), list) else None,
        limitations=list(config.get("limitations", [])) or None,
    )
    passport_path = Path(
        run_passport_path
        or config.get("runPassportPath", f"data/runs/{config['id']}-run-passport.json")
    )
    dossier = {
        "id": config["id"],
        "claimLevel": claim_level,
        "corridor": config["corridor"],
        "decisionQuestion": config["decisionQuestion"],
        "baseline": {
            "label": config["baseline"]["label"],
            "analyticsPath": config["baseline"].get("analyticsLogicalPath", config["baseline"]["analyticsPath"]),
            "summary": baseline.get("summary", {}),
        },
        "proposedMeasure": {
            "label": config["measure"]["label"],
            "type": config["measure"]["type"],
            "description": config["measure"].get("description", ""),
            "analyticsPath": config["measure"].get("analyticsLogicalPath", config["measure"]["analyticsPath"]),
            "summary": measure.get("summary", {}),
        },
        "experiment": _dossier_experiment(paired_result, config),
        "executiveKpis": executive_kpis,
        "assumptions": list(config.get("assumptions", [])),
        "sources": run_passport.get("dataSources", []),
        "risks": list(config.get("risks", [])),
        "capexOpex": config.get("costs", {}),
        "trustMetadata": run_passport,
        "limitations": run_passport.get("limitations", []),
        "recommendation": recommendation,
        "outputs": {},
    }

    destination = Path(output_dir or config.get("outputDir", f"reports/dossiers/{config['id']}"))
    paths = {
        "json": destination / "dossier.json",
        "markdown": destination / "dossier.md",
        "html": destination / "dossier.html",
        "kpisCsv": destination / "kpis.csv",
    }
    output_refs = {key: str(path) for key, path in paths.items()}
    logical_output_dir = config.get("outputLogicalDir")
    if logical_output_dir is not None:
        logical_root = Path(str(logical_output_dir))
        if logical_root.is_absolute() or ".." in logical_root.parts or any(
            ".staging" in part for part in logical_root.parts
        ):
            raise ValueError("outputLogicalDir must be a safe run-relative path")
        output_refs = {
            "json": (logical_root / "dossier.json").as_posix(),
            "markdown": (logical_root / "dossier.md").as_posix(),
            "html": (logical_root / "dossier.html").as_posix(),
            "kpisCsv": (logical_root / "kpis.csv").as_posix(),
        }
    destination.mkdir(parents=True, exist_ok=True)
    write_run_passport(run_passport, passport_path)
    _write_json(paths["json"], dossier)
    _write_markdown(paths["markdown"], dossier)
    _write_html(paths["html"], dossier)
    _write_kpis_csv(paths["kpisCsv"], executive_kpis)
    dossier["outputs"] = output_refs
    _write_json(paths["json"], dossier)
    return dossier


def _resolve_audit_run_id(config: dict[str, Any], *, release_run_id: str | None) -> str:
    configured = config.get("releaseRunId")
    if configured is not None and not isinstance(configured, str):
        raise ValueError("Dossier releaseRunId must be a string")
    if release_run_id is not None and configured is not None and release_run_id != configured:
        raise ValueError("Explicit release_run_id does not match dossier releaseRunId")
    selected = release_run_id or configured or str(config["id"])
    if not _RUN_ID_PATTERN.fullmatch(selected):
        raise ValueError(f"Dossier release run id is unsafe: {selected!r}")
    return selected


def _load_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")


def build_recommendation(executive_kpis: dict[str, Any], *, claim_level: str) -> dict[str, Any]:
    validate_claim_level(claim_level)
    _validate_recommendation_claim_inheritance(executive_kpis, claim_level=claim_level)
    by_id = kpis_by_id(executive_kpis)
    factors = [_classify_factor(by_id.get(kpi_id), kpi_id=kpi_id, direction=direction, tolerance=tolerance) for kpi_id, direction, tolerance in PRIMARY_KPI_RULES]
    evidence_limited = [item for item in factors if item["classification"] == "evidence_limited"]
    favorable = [item for item in factors if item["classification"] == "favorable"]
    unfavorable = [item for item in factors if item["classification"] == "unfavorable"]

    if evidence_limited:
        rule_id = "M1"
        mobility_state = "M1_evidence_limited"
        decision = "request_more_evidence"
    elif favorable and unfavorable:
        rule_id = "M2"
        mobility_state = "M2_mixed"
        decision = "request_more_evidence"
    elif unfavorable and not favorable:
        rule_id = "M3"
        mobility_state = "M3_unfavorable_only"
        decision = "reject"
    elif not favorable and not unfavorable:
        rule_id = "M4"
        mobility_state = "M4_all_neutral"
        decision = "request_more_evidence"
    else:
        rule_id = "M5"
        mobility_state = "M5_favorable_only"
        decision = ""

    economics_state, economics_checks = _economics_state(by_id)
    matrix_cell: str | None = None
    if rule_id == "M5":
        matrix = {
            "demo": {
                "E1_incomplete": "request_more_evidence",
                "E2_positive": "request_more_evidence",
                "E3_non_positive": "request_more_evidence",
            },
            "proxy": {
                "E1_incomplete": "request_more_evidence",
                "E2_positive": "request_more_evidence",
                "E3_non_positive": "request_more_evidence",
            },
            "calibrated": {
                "E1_incomplete": "request_more_evidence",
                "E2_positive": "defer",
                "E3_non_positive": "defer",
            },
            "real-data": {
                "E1_incomplete": "request_more_evidence",
                "E2_positive": "request_more_evidence",
                "E3_non_positive": "defer",
            },
            "procurement-ready": {
                "E1_incomplete": "request_more_evidence",
                "E2_positive": "fund_conditional_on_evidence",
                "E3_non_positive": "reject",
            },
        }
        decision = matrix[claim_level][economics_state]
        matrix_cell = f"{claim_level}:{economics_state}"
    rationale = _recommendation_rationale(
        mobility_state=mobility_state,
        economics_state=economics_state,
        claim_level=claim_level,
        decision=decision,
    )
    return {
        "decision": decision,
        "rationale": rationale,
        "allowedDecisions": [
            "request_more_evidence",
            "investigate_further",
            "defer",
            "fund_conditional_on_evidence",
            "reject",
        ],
        "claimLevel": claim_level,
        "ruleId": rule_id,
        "mobilityState": mobility_state,
        "primaryKpiIds": [item[0] for item in PRIMARY_KPI_RULES],
        "factors": factors,
        "economicsState": economics_state,
        "economicsKpiIds": list(ECONOMIC_KPI_IDS),
        "economicsChecks": economics_checks,
        "matrixCell": matrix_cell,
    }


def _validate_recommendation_claim_inheritance(
    executive_kpis: dict[str, Any], *, claim_level: str
) -> None:
    block_claim_level = executive_kpis.get("claimLevel")
    if block_claim_level != claim_level:
        raise ValueError(
            "Executive KPI block claimLevel must match the recommendation claim_level"
        )
    validate_claim_level(str(block_claim_level))

    confidence = executive_kpis.get("confidence")
    if not isinstance(confidence, dict) or confidence.get("claimLevel") != claim_level:
        raise ValueError(
            "Executive KPI confidence claimLevel must match the recommendation claim_level"
        )

    assumptions = executive_kpis.get("assumptions")
    if not isinstance(assumptions, dict):
        raise ValueError("Executive KPI block must contain an assumptions object")
    occupancy = _finite_or_none(assumptions.get("averageVehicleOccupancy"))
    if occupancy is None or occupancy <= 0:
        raise ValueError("Executive KPI averageVehicleOccupancy must be a finite positive number")
    if assumptions.get("averageVehicleOccupancyClaimLevel") != "proxy":
        raise ValueError("Executive KPI averageVehicleOccupancy assumption must retain proxy claim level")

    rows = executive_kpis.get("kpis")
    if not isinstance(rows, list):
        raise ValueError("Executive KPI block must contain a KPI list")
    seen_ids: set[str] = set()
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise ValueError(f"Executive KPI row {index} must be an object")
        kpi_id = row.get("id")
        if not isinstance(kpi_id, str) or not kpi_id:
            raise ValueError(f"Executive KPI row {index} must have a non-empty id")
        if kpi_id in seen_ids:
            raise ValueError(f"Executive KPI block contains duplicate id: {kpi_id}")
        seen_ids.add(kpi_id)
        if row.get("claimLevel") != claim_level:
            raise ValueError(
                f"Executive KPI row {kpi_id} claimLevel must match the recommendation claim_level"
            )
        validate_claim_level(str(row["claimLevel"]))


def _classify_factor(
    item: dict[str, Any] | None,
    *,
    kpi_id: str,
    direction: str,
    tolerance: float,
) -> dict[str, Any]:
    factor = {
        "id": kpi_id,
        "direction": direction,
        "tolerance": tolerance,
        "delta": None,
        "available": False,
        "clampAffected": False,
        "clampReason": None,
        "classification": "evidence_limited",
        "reason": "KPI is missing.",
    }
    if not isinstance(item, dict):
        return factor
    factor["available"] = bool(item.get("available", False))
    factor["clampAffected"] = bool(item.get("clampAffected", False))
    factor["clampReason"] = item.get("clampReason")
    if item.get("direction") != direction:
        factor["reason"] = f"Expected direction {direction}; got {item.get('direction')}."
        return factor
    delta = _finite_or_none(item.get("delta"))
    factor["delta"] = delta
    if not factor["available"]:
        factor["reason"] = "KPI is unavailable."
        return factor
    if factor["clampAffected"]:
        factor["reason"] = str(factor["clampReason"] or "A proxy clamp is active.")
        return factor
    if delta is None:
        factor["reason"] = "KPI delta is not finite."
        return factor
    if abs(delta) <= tolerance:
        factor["classification"] = "neutral"
        factor["reason"] = "Absolute serialized delta is within tolerance."
    elif (direction == "lower_is_better" and delta < 0) or (direction == "higher_is_better" and delta > 0):
        factor["classification"] = "favorable"
        factor["reason"] = "Serialized delta is favorable after applying direction."
    else:
        factor["classification"] = "unfavorable"
        factor["reason"] = "Serialized delta is unfavorable after applying direction."
    return factor


def _economics_state(by_id: dict[str, dict[str, Any]]) -> tuple[str, list[dict[str, Any]]]:
    checks: list[dict[str, Any]] = []
    incomplete = False
    values: dict[str, float | None] = {}
    for kpi_id in ECONOMIC_KPI_IDS:
        item = by_id.get(kpi_id)
        available = isinstance(item, dict) and bool(item.get("available", False))
        placeholder_sensitive = kpi_id in {"capex_placeholder", "opex_placeholder", "roi_proxy", "payback_proxy"}
        placeholder = bool(item.get("placeholder", False)) if isinstance(item, dict) else False
        value = _finite_or_none(item.get("measure")) if isinstance(item, dict) else None
        complete = available and value is not None and not (placeholder_sensitive and placeholder)
        if not complete:
            incomplete = True
        values[kpi_id] = value
        checks.append(
            {
                "id": kpi_id,
                "available": available,
                "placeholder": placeholder,
                "value": value,
                "complete": complete,
            }
        )
    if incomplete:
        return "E1_incomplete", checks
    capex = values["capex_placeholder"]
    opex = values["opex_placeholder"]
    savings = values["annual_time_savings_proxy"]
    roi = values["roi_proxy"]
    payback = values["payback_proxy"]
    positive = bool(
        capex is not None
        and opex is not None
        and savings is not None
        and roi is not None
        and payback is not None
        and capex > 0
        and opex >= 0
        and savings > opex
        and roi > 0
        and payback > 0
    )
    return ("E2_positive" if positive else "E3_non_positive"), checks


def _recommendation_rationale(
    *, mobility_state: str, economics_state: str, claim_level: str, decision: str
) -> str:
    if mobility_state == "M1_evidence_limited":
        return "At least one primary KPI is unavailable or clamp-affected; collect stronger evidence before a decision."
    if mobility_state == "M2_mixed":
        return "Primary mobility KPI directions are mixed; investigate the trade-offs before a decision."
    if mobility_state == "M3_unfavorable_only":
        return "Available primary mobility KPIs are unfavorable and provide no favorable counter-signal."
    if mobility_state == "M4_all_neutral":
        return "Primary mobility KPI deltas are within tolerance and do not support an intervention decision."
    if claim_level in {"demo", "proxy"}:
        return "Primary proxy KPI directions are favorable, but the claim level and cost evidence do not support a clean funding decision."
    if claim_level == "real-data":
        return "Real-data describes input provenance, not model calibration; calibration evidence is still required before a funding recommendation."
    if economics_state == "E1_incomplete":
        return "Primary KPI directions are favorable, but required economic evidence is incomplete or placeholder-sensitive."
    return f"The exhaustive claim/economics gate maps favorable primary KPIs to {decision}."


def _finite_or_none(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _load_and_verify_pair(
    config: dict[str, Any],
    *,
    baseline: dict[str, Any],
    measure: dict[str, Any],
    schema_path: str | Path | None = None,
) -> dict[str, Any]:
    pair_path = config.get("pairedExperimentPath")
    if not pair_path:
        raise ValueError("Dossier pairedExperimentPath is required for abay-signal-retiming")
    pair = _load_json(pair_path)
    validate_paired_experiment_result(pair, schema_path=schema_path)
    if pair["scenarioId"] != config["id"]:
        raise ValueError("Selected paired experiment scenarioId does not match dossier config")
    if pair["corridorId"] != config["corridor"]["id"]:
        raise ValueError("Selected paired experiment corridorId does not match dossier config")
    if pair["claimLevel"] != config.get("claimLevel", "proxy"):
        raise ValueError("Selected paired experiment claimLevel does not match dossier config")
    baseline_delay = config["baseline"].get("scenario", {}).get("signal_delay_s")
    measure_delay = config["measure"].get("scenario", {}).get("signal_delay_s")
    if baseline_delay != pair["baseline"]["signalDelaySeconds"]:
        raise ValueError("Selected paired experiment baseline delay does not match dossier config")
    if measure_delay != pair["measure"]["signalDelaySeconds"]:
        raise ValueError("Selected paired experiment measure delay does not match dossier config")
    if canonical_json(pair["baseline"]["analytics"]) != canonical_json(baseline):
        raise ValueError("Selected baseline analytics do not match paired experiment result")
    if canonical_json(pair["measure"]["analytics"]) != canonical_json(measure):
        raise ValueError("Selected measure analytics do not match paired experiment result")
    return pair


def _dossier_experiment(pair: dict[str, Any] | None, config: dict[str, Any]) -> dict[str, Any] | None:
    if pair is None:
        return None
    return {
        "schemaVersion": pair["schemaVersion"],
        "modelId": pair["modelId"],
        "scenarioId": pair["scenarioId"],
        "semanticFingerprint": pair["semanticFingerprint"],
        "pairResultPath": config.get("pairedExperimentLogicalPath", config.get("pairedExperimentPath")),
        "controlledDifferences": pair["experiment"]["controlledDifferences"],
        "unchangedFields": pair["experiment"]["unchangedFields"],
        "demandControl": pair["experiment"]["demandControl"],
        "baseSeriesFingerprint": pair["experiment"]["baseSeriesFingerprint"],
        "contextNetworkFingerprint": pair["experiment"]["contextNetworkFingerprint"],
        "proxyModel": pair["proxyModel"],
    }


def _validate_dossier_config(config: dict[str, Any]) -> None:
    if config.get("id") != "abay-signal-retiming":
        raise ValueError("Only the abay-signal-retiming dossier is supported by this controlled pair")
    if config.get("claimLevel") != "proxy":
        raise ValueError("abay-signal-retiming dossier claimLevel must be proxy")
    corridor = config.get("corridor")
    if not isinstance(corridor, dict) or corridor.get("id") != "abay":
        raise ValueError("Controlled dossier corridor must be abay")
    baseline = config.get("baseline")
    measure = config.get("measure")
    if not isinstance(baseline, dict) or not baseline.get("analyticsPath"):
        raise ValueError("Dossier baseline.analyticsPath is required")
    if not isinstance(measure, dict) or measure.get("type") != "signal_retiming" or not measure.get("analyticsPath"):
        raise ValueError("Dossier measure must be signal_retiming with analyticsPath")
    for role, variant in (("baseline", baseline), ("measure", measure)):
        scenario = variant.get("scenario")
        if not isinstance(scenario, dict) or scenario.get("claim_level") != "proxy":
            raise ValueError(f"Dossier {role}.scenario.claim_level must be proxy")
        delay = scenario.get("signal_delay_s")
        if isinstance(delay, bool) or not isinstance(delay, (int, float)):
            raise ValueError(f"Dossier {role}.scenario.signal_delay_s is required")
    if not config.get("pairedExperimentPath"):
        raise ValueError("Dossier pairedExperimentPath is required for abay-signal-retiming")
    if "closed_streets" in canonical_json(config) or "closedStreets" in canonical_json(config):
        raise ValueError("closed_streets semantics are not valid for Abay signal retiming")


def _write_kpis_csv(path: Path, executive_kpis: dict[str, Any]) -> None:
    with path.open("w", newline="", encoding="utf-8") as file:
        fieldnames = [
            "id",
            "label",
            "unit",
            "baseline",
            "measure",
            "delta",
            "direction",
            "claimLevel",
            "formula",
            "placeholder",
            "available",
            "clampAffected",
            "clampReason",
        ]
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for item in executive_kpis.get("kpis", []):
            writer.writerow({key: item.get(key) for key in fieldnames})


def _write_markdown(path: Path, dossier: dict[str, Any]) -> None:
    kpi_rows = "\n".join(
        f"| `{item.get('id')}` | {item.get('label')} | {item.get('unit')} | {item.get('baseline')} | {item.get('measure')} | {item.get('delta')} | `{item.get('claimLevel')}` |"
        for item in dossier["executiveKpis"].get("kpis", [])
    )
    source_rows = "\n".join(
        f"| {source.get('label')} | `{source.get('path')}` | `{source.get('claim_label')}` | {source.get('available')} | {source.get('notes')} |"
        for source in dossier.get("sources", [])
    )
    assumptions = "\n".join(f"- {item}" for item in dossier.get("assumptions", []))
    risks = "\n".join(f"- {item}" for item in dossier.get("risks", []))
    limitations = "\n".join(f"- {item}" for item in dossier.get("limitations", []))
    path.write_text(
        f"""# Scenario Dossier: {dossier['corridor']['name']} - {dossier['proposedMeasure']['label']}

Claim level: `proxy`

## Decision Question

{dossier['decisionQuestion']}

## Recommendation

**{dossier['recommendation']['decision']}**: {dossier['recommendation']['rationale']}

## Baseline

- Label: {dossier['baseline']['label']}
- Analytics: `{dossier['baseline']['analyticsPath']}`
- Summary: `{json.dumps(dossier['baseline']['summary'], ensure_ascii=True)}`

## Proposed Measure

- Label: {dossier['proposedMeasure']['label']}
- Type: `{dossier['proposedMeasure']['type']}`
- Analytics: `{dossier['proposedMeasure']['analyticsPath']}`
- Description: {dossier['proposedMeasure']['description']}

## Executive KPI Deltas

| KPI | Label | Unit | Baseline | Measure | Delta | Claim |
|---|---|---:|---:|---:|---:|---|
{kpi_rows}

## CAPEX/OPEX Placeholders

- CAPEX: {dossier['capexOpex'].get('capexKzt')} KZT
- OPEX: {dossier['capexOpex'].get('opexKztPerYear')} KZT/year
- Claim level: `{dossier['capexOpex'].get('claimLevel', 'proxy')}`
- Notes: {dossier['capexOpex'].get('notes', '')}

## Assumptions

{assumptions}

## Sources

| Source | Path | Claim | Available | Notes |
|---|---|---|---:|---|
{source_rows}

## Risks

{risks}

## Trust Metadata

- Run ID: `{dossier['trustMetadata'].get('runId')}`
- Seed: `{dossier['trustMetadata'].get('seed')}`
- Git hash: `{dossier['trustMetadata'].get('model', {}).get('gitHash')}`
- Claim labels: `{json.dumps(dossier['trustMetadata'].get('claimLabels', {}), ensure_ascii=True)}`

## Limitations

{limitations}
""",
        encoding="utf-8",
    )


def _write_html(path: Path, dossier: dict[str, Any]) -> None:
    markdown = (path.parent / "dossier.md").read_text(encoding="utf-8")
    escaped = html.escape(markdown)
    path.write_text(
        f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Scenario Dossier - {html.escape(str(dossier['corridor']['name']))}</title>
  <style>
    body {{ font-family: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; max-width: 1040px; margin: 32px auto; padding: 0 24px; color: #1f2729; }}
    pre {{ white-space: pre-wrap; background: #f6f3ec; border: 1px solid #ddd4c7; border-radius: 8px; padding: 20px; line-height: 1.5; }}
  </style>
</head>
<body>
  <pre>{escaped}</pre>
</body>
</html>
""",
        encoding="utf-8",
    )
