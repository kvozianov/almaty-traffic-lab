from __future__ import annotations

from datetime import datetime, timezone
import csv
import hashlib
import json
from pathlib import Path
from pathlib import PurePosixPath
from typing import Any, Mapping


WORKFLOW_STATUSES = ("draft", "reviewed", "approved", "assigned", "deployed", "monitored", "audited")
DEFAULT_DOSSIER_PATH = Path("reports/dossiers/abay-signal-retiming/dossier.json")
DEFAULT_WORKFLOW_DIR = Path("reports/workflows")

REQUIRED_INPUT_ROLES = ("dossierJson", "dossierMarkdown", "runPassport")
OPTIONAL_INPUT_ROLES = ("dossierHtml", "kpiCsv")
OUTPUT_ROLES = ("workflowJson", "engineerTasksCsv", "monitoringJson", "postAuditJson")
STATIC_REF_ROLES = ("claimLedger",)


def generate_decision_workflow(
    dossier_path: str | Path = DEFAULT_DOSSIER_PATH,
    *,
    out_dir: str | Path = DEFAULT_WORKFLOW_DIR,
    dossier: dict[str, Any] | None = None,
    artifact_paths: Mapping[str, str | Path] | None = None,
    artifact_refs: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Generate a complete demonstrator workflow from dossier to post-audit."""

    explicit_context = artifact_paths is not None
    resolved_paths, resolved_refs = _resolve_artifact_context(
        dossier_path=Path(dossier_path),
        dossier=dossier,
        out_dir=Path(out_dir),
        artifact_paths=artifact_paths,
        artifact_refs=artifact_refs,
    )
    dossier_path = resolved_paths["dossierJson"]
    dossier = dossier or _load_json(dossier_path)
    workflow_id = f"{_safe_id(str(dossier.get('id', 'scenario')))}-decision-workflow"
    output_dir = Path(out_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    workflow_path = output_dir / f"{workflow_id}.json"
    task_path = output_dir / f"{workflow_id}-engineer-tasks.csv"
    monitoring_path = output_dir / f"{workflow_id}-monitoring.json"
    post_audit_path = output_dir / f"{workflow_id}-post-audit.json"

    _write_engineer_tasks(
        dossier,
        task_path,
        evidence_refs=resolved_refs if explicit_context else None,
    )
    _write_monitoring_plan(dossier, monitoring_path)
    post_audit = build_forecast_vs_fact_audit(dossier)
    post_audit["evidencePath"] = (
        resolved_refs["postAuditJson"] if explicit_context else str(post_audit_path)
    )
    post_audit_path.write_text(json.dumps(post_audit, indent=2, ensure_ascii=True), encoding="utf-8")

    if explicit_context:
        workflow = create_workflow(
            dossier_path,
            dossier=dossier,
            artifact_paths={
                role: path
                for role, path in resolved_paths.items()
                if role in REQUIRED_INPUT_ROLES + OPTIONAL_INPUT_ROLES
            },
            artifact_refs={
                role: ref
                for role, ref in resolved_refs.items()
                if role in set(resolved_paths) | set(OUTPUT_ROLES) | set(STATIC_REF_ROLES)
            },
        )
    else:
        workflow = create_workflow(dossier_path, dossier=dossier)
    workflow["outputs"] = {role: resolved_refs[role] for role in OUTPUT_ROLES}
    transition_workflow(
        workflow,
        "reviewed",
        owner="transport-planning-reviewer",
        evidence_path=dossier_path,
        evidence_ref=resolved_refs["dossierJson"] if explicit_context else None,
        comments="Dossier reviewed against claim labels, limitations, and recommendation.",
        next_action="Seek approval for evidence collection and engineering review, not funding.",
    )
    transition_workflow(
        workflow,
        "approved",
        owner="chief-transport-officer",
        evidence_path=resolved_paths["dossierMarkdown"],
        evidence_ref=resolved_refs["dossierMarkdown"] if explicit_context else None,
        comments="Approved to assign engineering due diligence; dossier recommendation remains defer for funding.",
        next_action="Export engineer tasks and lock dossier artifact versions.",
    )
    transition_workflow(
        workflow,
        "assigned",
        owner="signal-engineering-lead",
        evidence_path=task_path,
        evidence_ref=resolved_refs["engineerTasksCsv"] if explicit_context else None,
        comments="Engineering, police, bus operations, and data tasks exported.",
        next_action="Track field deployment prerequisites.",
    )
    transition_workflow(
        workflow,
        "deployed",
        owner="field-operations-lead",
        evidence_path=task_path,
        evidence_ref=resolved_refs["engineerTasksCsv"] if explicit_context else None,
        comments="Demo deployment record: tasks are marked as ready for controlled pilot, not completed field work.",
        next_action="Start monitoring plan and collect observed speed, queue, and bus reliability evidence.",
    )
    transition_workflow(
        workflow,
        "monitored",
        owner="traffic-data-analyst",
        evidence_path=monitoring_path,
        evidence_ref=resolved_refs["monitoringJson"] if explicit_context else None,
        comments="Monitoring plan created with required observed metrics and source gaps.",
        next_action="Compare forecast KPIs against observed facts and decide whether recalibration is required.",
    )
    transition_workflow(
        workflow,
        "audited",
        owner="model-governance-reviewer",
        evidence_path=post_audit_path,
        evidence_ref=resolved_refs["postAuditJson"] if explicit_context else None,
        comments="Forecast-vs-fact post-audit attached; recalibration remains required before stronger claims.",
        next_action="Attach observed municipal data and rerun dossier before any procurement-ready language.",
        forecast_vs_fact=post_audit,
    )
    workflow_path.write_text(json.dumps(workflow, indent=2, ensure_ascii=True), encoding="utf-8")
    return workflow


def create_workflow(
    dossier_path: str | Path,
    *,
    dossier: dict[str, Any] | None = None,
    artifact_paths: Mapping[str, str | Path] | None = None,
    artifact_refs: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    dossier_path = Path(dossier_path)
    dossier = dossier or _load_json(dossier_path)
    resolved_paths, resolved_refs = _resolve_artifact_context(
        dossier_path=dossier_path,
        dossier=dossier,
        out_dir=DEFAULT_WORKFLOW_DIR,
        artifact_paths=artifact_paths,
        artifact_refs=artifact_refs,
        require_output_refs=artifact_paths is not None,
    )
    workflow_id = f"{_safe_id(str(dossier.get('id', 'scenario')))}-decision-workflow"
    now = _now()
    input_roles = [role for role in REQUIRED_INPUT_ROLES + OPTIONAL_INPUT_ROLES if role in resolved_paths]
    return {
        "id": workflow_id,
        "kind": "closed-decision-workflow",
        "claimLevel": "demo",
        "scenarioId": dossier.get("id"),
        "status": "draft",
        "statusSequence": list(WORKFLOW_STATUSES),
        "createdAt": now,
        "updatedAt": now,
        "dossier": {
            "path": resolved_refs["dossierJson"],
            "claimLevel": dossier.get("claimLevel", "proxy"),
            "recommendation": dossier.get("recommendation", {}),
            "artifactPaths": [resolved_refs[role] for role in input_roles],
        },
        "artifactLocks": _artifact_locks(
            {role: resolved_paths[role] for role in input_roles},
            {role: resolved_refs[role] for role in input_roles},
        ),
        "history": [
            _history_item(
                from_status=None,
                to_status="draft",
                owner="planning-analyst",
                evidence_path=resolved_paths["dossierJson"],
                evidence_ref=resolved_refs["dossierJson"],
                comments="Workflow opened from Scenario Dossier artifact.",
                next_action="Review dossier evidence and claim labels.",
            )
        ],
        "currentOwner": "planning-analyst",
        "limitations": [
            "Workflow state is a local demonstrator until connected to authenticated municipal users.",
            "Approvals record evidence and owner fields but are not legal electronic signatures.",
            "Deployment and monitoring records are demo/proxy until linked to field work orders and observed feeds.",
            "Forecast-vs-fact comparison uses demonstrator observed values unless replaced with real measured outcomes.",
        ],
    }


def transition_workflow(
    workflow: dict[str, Any],
    to_status: str,
    *,
    owner: str,
    evidence_path: str | Path,
    evidence_ref: str | None = None,
    comments: str,
    next_action: str,
    forecast_vs_fact: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if to_status not in WORKFLOW_STATUSES:
        raise ValueError(f"Unsupported workflow status: {to_status}")
    current = str(workflow.get("status", "draft"))
    expected = _next_status(current)
    if expected != to_status:
        raise ValueError(f"Invalid workflow transition: {current} -> {to_status}; expected {expected}")
    evidence = Path(evidence_path)
    if not evidence.exists():
        raise FileNotFoundError(f"Workflow transition evidence does not exist: {evidence}")
    item = _history_item(
        from_status=current,
        to_status=to_status,
        owner=owner,
        evidence_path=evidence,
        evidence_ref=evidence_ref,
        comments=comments,
        next_action=next_action,
    )
    if forecast_vs_fact is not None:
        item["forecastVsFact"] = forecast_vs_fact
        item["recalibrationRequired"] = bool(forecast_vs_fact.get("recalibrationRequired"))
    workflow.setdefault("history", []).append(item)
    workflow["status"] = to_status
    workflow["currentOwner"] = owner
    workflow["updatedAt"] = item["timestamp"]
    workflow["evidenceCompleteness"] = _evidence_completeness(workflow)
    return workflow


def build_forecast_vs_fact_audit(
    dossier: dict[str, Any],
    observed_values: dict[str, float] | None = None,
) -> dict[str, Any]:
    observed_values = observed_values or _demo_observed_values(dossier)
    items = []
    for kpi in dossier.get("executiveKpis", {}).get("kpis", []):
        if not isinstance(kpi, dict):
            continue
        kpi_id = str(kpi.get("id"))
        if kpi_id not in observed_values:
            continue
        forecast = _forecast_value(kpi)
        observed = float(observed_values[kpi_id])
        error = observed - forecast
        pct = abs(error) / abs(forecast) if forecast else None
        items.append(
            {
                "kpiId": kpi_id,
                "label": kpi.get("label"),
                "unit": kpi.get("unit"),
                "forecastValue": round(forecast, 3),
                "observedValue": round(observed, 3),
                "error": round(error, 3),
                "absoluteErrorPct": round(pct, 3) if pct is not None else None,
                "claimLevel": "demo",
                "formula": kpi.get("formula"),
            }
        )
    max_error = max((item["absoluteErrorPct"] or 0.0 for item in items), default=0.0)
    return {
        "kind": "forecast-vs-fact-audit",
        "claimLevel": "demo",
        "createdAt": _now(),
        "scenarioId": dossier.get("id"),
        "comparisonMethod": "Demo observed values compared against dossier KPI forecast values; replace with measured outcomes before stronger claims.",
        "items": items,
        "recalibrationRequired": max_error > 0.15,
        "maxAbsoluteErrorPct": round(max_error, 3),
        "nextAction": "Attach observed speed, queue, bus reliability, cost, and emissions data; rerun calibration and dossier.",
        "limitations": [
            "Observed values are demonstrator inputs unless replaced by municipal data.",
            "This audit is evidence structure, not validation of real-world effectiveness.",
        ],
    }


def _write_engineer_tasks(
    dossier: dict[str, Any],
    path: Path,
    *,
    evidence_refs: Mapping[str, str] | None = None,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    dossier_json_ref = (
        evidence_refs["dossierJson"]
        if evidence_refs is not None
        else str(dossier.get("outputs", {}).get("json", ""))
    )
    dossier_markdown_ref = (
        evidence_refs["dossierMarkdown"]
        if evidence_refs is not None
        else str(dossier.get("outputs", {}).get("markdown", ""))
    )
    workflow_dir_ref = (
        PurePosixPath(evidence_refs["workflowJson"]).parent.as_posix()
        if evidence_refs is not None
        else "reports/workflows/"
    )
    claim_ledger_ref = (
        evidence_refs["claimLedger"]
        if evidence_refs is not None
        else "docs/obsidian/03-registries/Claim Ledger.md"
    )
    rows = [
        {
            "task_id": "ENG-001",
            "owner": "signal-engineering-lead",
            "task": "Review signal timing feasibility and controller constraints for Abay.",
            "evidence_source": dossier_json_ref,
            "required_before_status": "deployed",
            "claim_level": "demo",
        },
        {
            "task_id": "OPS-002",
            "owner": "traffic-police-coordinator",
            "task": "Confirm field authority, safety constraints, and public transport conflicts.",
            "evidence_source": dossier_markdown_ref,
            "required_before_status": "deployed",
            "claim_level": "demo",
        },
        {
            "task_id": "DATA-003",
            "owner": "traffic-data-analyst",
            "task": "Collect observed speed, queue/load, and bus reliability after pilot window.",
            "evidence_source": workflow_dir_ref,
            "required_before_status": "audited",
            "claim_level": "demo",
        },
        {
            "task_id": "PROC-004",
            "owner": "procurement-analyst",
            "task": "Replace CAPEX/OPEX placeholders with sourced engineering estimates.",
            "evidence_source": claim_ledger_ref,
            "required_before_status": "procurement-review",
            "claim_level": "demo",
        },
    ]
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _write_monitoring_plan(dossier: dict[str, Any], path: Path) -> None:
    payload = {
        "kind": "post-implementation-monitoring-plan",
        "claimLevel": "demo",
        "scenarioId": dossier.get("id"),
        "requiredObservedFields": [
            "observed average corridor speed",
            "observed queue/load proxy",
            "observed bus reliability",
            "actual CAPEX/OPEX",
            "implementation timestamp",
            "field approval record",
        ],
        "monitoringWindow": "first 7 operating days after controlled pilot",
        "sourceGaps": [
            "No live municipal detector/camera feed attached.",
            "No field work order system attached.",
            "No verified cost ledger attached.",
        ],
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")


def _history_item(
    *,
    from_status: str | None,
    to_status: str,
    owner: str,
    evidence_path: str | Path,
    evidence_ref: str | None = None,
    comments: str,
    next_action: str,
) -> dict[str, Any]:
    evidence = Path(evidence_path)
    return {
        "fromStatus": from_status,
        "toStatus": to_status,
        "owner": owner,
        "timestamp": _now(),
        "evidencePath": (
            _logical_ref(evidence_ref, role="workflowEvidence")
            if evidence_ref is not None
            else str(evidence)
        ),
        "evidenceSha256": _sha256(evidence) if evidence.exists() and evidence.is_file() else None,
        "comments": comments,
        "nextAction": next_action,
        "requiredEvidenceSatisfied": evidence.exists(),
        "claimLevel": "demo",
    }


def _artifact_locks(
    paths: Mapping[str, Path],
    refs: Mapping[str, str],
) -> list[dict[str, Any]]:
    return [
        {
            "path": refs[role],
            "available": path.exists(),
            "sha256": _sha256(path) if path.exists() and path.is_file() else None,
            "bytes": path.stat().st_size if path.exists() and path.is_file() else None,
        }
        for role, path in paths.items()
    ]


def _resolve_artifact_context(
    *,
    dossier_path: Path,
    dossier: dict[str, Any] | None,
    out_dir: Path,
    artifact_paths: Mapping[str, str | Path] | None,
    artifact_refs: Mapping[str, str] | None,
    require_output_refs: bool = True,
) -> tuple[dict[str, Path], dict[str, str]]:
    if artifact_paths is None:
        if artifact_refs is not None:
            raise ValueError("artifact_paths is required when artifact_refs is explicit")
        payload = dossier or _load_json(dossier_path)
        outputs = payload.get("outputs", {}) if isinstance(payload.get("outputs"), dict) else {}
        scenario_id = _safe_id(str(payload.get("id", "scenario")))
        physical: dict[str, Path] = {
            "dossierJson": dossier_path,
            "dossierMarkdown": Path(outputs.get("markdown") or dossier_path.with_suffix(".md")),
            "runPassport": Path("data/runs") / f"{scenario_id}-run-passport.json",
        }
        optional_output_keys = {"dossierHtml": "html", "kpiCsv": "kpisCsv"}
        for role, output_key in optional_output_keys.items():
            value = outputs.get(output_key)
            if isinstance(value, str) and value:
                physical[role] = Path(value)
        workflow_id = f"{scenario_id}-decision-workflow"
        physical.update(_workflow_output_paths(out_dir, workflow_id))
        refs = {role: str(path) for role, path in physical.items()}
        refs["claimLedger"] = "docs/obsidian/03-registries/Claim Ledger.md"
        return physical, refs

    required = set(REQUIRED_INPUT_ROLES)
    allowed = required | set(OPTIONAL_INPUT_ROLES)
    actual = set(artifact_paths)
    missing = sorted(required - actual)
    unknown = sorted(actual - allowed)
    if missing or unknown:
        raise ValueError(f"Invalid artifact_paths: missing={missing}, unknown={unknown}")
    if artifact_refs is None:
        raise ValueError("artifact_refs is required when artifact_paths is explicit")

    physical = {role: Path(path) for role, path in artifact_paths.items()}
    payload = dossier or _load_json(physical["dossierJson"])
    workflow_id = f"{_safe_id(str(payload.get('id', 'scenario')))}-decision-workflow"
    physical.update(_workflow_output_paths(out_dir, workflow_id))
    expected_refs = set(artifact_paths) | set(STATIC_REF_ROLES)
    if require_output_refs:
        expected_refs |= set(OUTPUT_ROLES)
    _require_exact_roles(artifact_refs, expected_refs, map_name="artifact_refs")
    refs = {
        role: _logical_ref(artifact_refs[role], role=role)
        for role in expected_refs
    }
    if not require_output_refs:
        refs.update({role: str(physical[role]) for role in OUTPUT_ROLES})
    return physical, refs


def _workflow_output_paths(out_dir: Path, workflow_id: str) -> dict[str, Path]:
    return {
        "workflowJson": out_dir / f"{workflow_id}.json",
        "engineerTasksCsv": out_dir / f"{workflow_id}-engineer-tasks.csv",
        "monitoringJson": out_dir / f"{workflow_id}-monitoring.json",
        "postAuditJson": out_dir / f"{workflow_id}-post-audit.json",
    }


def _require_exact_roles(
    values: Mapping[str, object],
    expected: set[str],
    *,
    map_name: str,
) -> None:
    actual = set(values)
    missing = sorted(expected - actual)
    unknown = sorted(actual - expected)
    if missing or unknown:
        raise ValueError(f"Invalid {map_name}: missing={missing}, unknown={unknown}")


def _logical_ref(value: str, *, role: str) -> str:
    raw = str(value)
    path = PurePosixPath(raw)
    if (
        not raw
        or raw != raw.strip()
        or "\\" in raw
        or path.is_absolute()
        or ".." in path.parts
        or any(".staging" in part for part in path.parts)
        or (path.parts and path.parts[0].endswith(":"))
        or path.as_posix() != raw
    ):
        raise ValueError(f"Unsafe logical reference for {role}: {raw!r}")
    return path.as_posix()


def _evidence_completeness(workflow: dict[str, Any]) -> dict[str, Any]:
    history = workflow.get("history", [])
    satisfied = sum(1 for item in history if item.get("requiredEvidenceSatisfied"))
    return {
        "historyCount": len(history),
        "satisfiedEvidenceCount": satisfied,
        "allRequiredEvidencePresent": satisfied == len(history),
    }


def _demo_observed_values(dossier: dict[str, Any]) -> dict[str, float]:
    values: dict[str, float] = {}
    for kpi in dossier.get("executiveKpis", {}).get("kpis", []):
        if not isinstance(kpi, dict):
            continue
        kpi_id = str(kpi.get("id"))
        forecast = _forecast_value(kpi)
        if kpi_id == "person_hours_saved":
            values[kpi_id] = forecast * 0.82
        elif kpi_id == "corridor_speed_delta":
            values[kpi_id] = forecast * 0.65
        elif kpi_id == "queue_load_proxy":
            values[kpi_id] = forecast + 0.04
        elif kpi_id == "bus_reliability_proxy":
            values[kpi_id] = forecast * 0.9
    return values


def _forecast_value(kpi: dict[str, Any]) -> float:
    if kpi.get("id") in {"person_hours_saved", "roi_proxy", "payback_proxy"}:
        return float(kpi.get("measure", 0.0) or 0.0)
    return float(kpi.get("delta", kpi.get("measure", 0.0)) or 0.0)


def _next_status(current: str) -> str | None:
    try:
        index = WORKFLOW_STATUSES.index(current)
    except ValueError as exc:
        raise ValueError(f"Unknown current workflow status: {current}") from exc
    if index + 1 >= len(WORKFLOW_STATUSES):
        return None
    return WORKFLOW_STATUSES[index + 1]


def _load_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_id(value: str) -> str:
    return "".join(char if char.isalnum() or char in {"-", "_"} else "-" for char in value.lower()).strip("-") or "workflow"


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
