from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from hashlib import sha256
from html import escape
import json
from pathlib import Path
from pathlib import PurePosixPath
from typing import Any, Mapping


DEFAULT_AKIMAT_DIR = Path("reports/akimat/abay-signal-retiming")

DOSSIER_PATH = Path("reports/dossiers/abay-signal-retiming/dossier.json")
SCENARIO_CONFIG_PATH = Path("data/scenarios/dossier_abay_signal.json")
RUN_PASSPORT_PATH = Path("data/runs/abay-signal-retiming-run-passport.json")
PROVIDER_REGISTRY_PATH = Path("reports/data_sources/provider_registry.json")
ROADS_PROVIDER_STATUS_PATH = Path("reports/data_sources/roads_geojson_provider_status.json")
WORKFLOW_PATH = Path("reports/workflows/abay-signal-retiming-decision-workflow.json")
TENDER_CHECKLIST_PATH = Path("reports/procurement/tender_checklist.json")
REPRO_MANIFEST_PATH = Path("reports/repro/abay/artifact_manifest.json")
REPRO_METADATA_PATH = Path("reports/repro/abay/metadata.json")
PORTFOLIO_RESULTS_PATH = Path("reports/portfolio/month1/portfolio_results.json")
PORTFOLIO_MATRIX_PATH = Path("reports/portfolio/month1/kpi_matrix.csv")
RESEARCH_APPENDIX_PATH = Path("reports/research_metrics/abay-signal-retiming/dossier_appendix.md")

REQUIRED_INPUT_PATHS: dict[str, Path] = {
    "dossier": DOSSIER_PATH,
    "scenarioConfig": SCENARIO_CONFIG_PATH,
    "runPassport": RUN_PASSPORT_PATH,
    "providers": PROVIDER_REGISTRY_PATH,
    "workflow": WORKFLOW_PATH,
    "procurement": TENDER_CHECKLIST_PATH,
    "reproManifest": REPRO_MANIFEST_PATH,
    "reproMetadata": REPRO_METADATA_PATH,
    "portfolioResults": PORTFOLIO_RESULTS_PATH,
}
OPTIONAL_INPUT_PATHS: dict[str, Path] = {
    "dossierMarkdown": DOSSIER_PATH.with_suffix(".md"),
    "roadsProviderStatus": ROADS_PROVIDER_STATUS_PATH,
    "portfolioMatrix": PORTFOLIO_MATRIX_PATH,
    "researchAppendix": RESEARCH_APPENDIX_PATH,
}
GENERATED_FILE_ROLES = (
    "application_summary_md",
    "application_summary_html",
    "data_request_memo_md",
    "data_readiness_json",
    "missing_evidence_json",
    "pilot_acceptance_criteria_json",
    "pilot_monitoring_plan_json",
    "pilot_monitoring_plan_md",
    "executive_brief_md",
    "demo_script_md",
    "slide_outline_md",
    "risk_register_json",
    "scenario_alternative_comparison_json",
    "scenario_alternative_comparison_md",
    "claim_boundary_md",
    "local_onprem_deployment_note_md",
    "evidence_manifest_json",
    "procurement_pack_index_json",
    "application_package_index_json",
)

SAFE_POSITION = (
    "The prototype can generate a reproducible proxy-level Abay Scenario Dossier "
    "with run metadata, KPI deltas, source labels, limitations, workflow evidence, "
    "and procurement checklist artifacts."
)


@dataclass(frozen=True, slots=True)
class AkimatDataRequest:
    id: str
    dataset: str
    requested_owner: str
    why_needed: str
    minimum_format: str
    current_claim_level: str
    claim_upgrade_use: str


@dataclass(frozen=True, slots=True)
class PilotCriterion:
    id: str
    kpi_id: str
    owner: str
    data_source: str
    baseline_window: str
    pilot_window: str
    acceptable_threshold: str
    recalibration_trigger: str
    decision_use: str
    current_claim_level: str


@dataclass(frozen=True, slots=True)
class RiskItem:
    id: str
    area: str
    risk: str
    severity: str
    mitigation: str
    evidence_needed: str
    claim_level: str


def generate_akimat_application_pack(
    out_dir: str | Path = DEFAULT_AKIMAT_DIR,
    *,
    inputs: Mapping[str, str | Path] | None = None,
    evidence_refs: Mapping[str, str] | None = None,
    output_refs: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Generate the Abay Akimat pilot/application pack from existing artifacts."""

    output_dir = Path(out_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    created_at = _utc_now()

    physical_inputs, logical_refs = _resolve_input_context(inputs, evidence_refs)
    resolved_output_refs = _resolve_output_refs(output_dir, output_refs, explicit=inputs is not None)

    dossier = _load_json(physical_inputs["dossier"])
    scenario_config = _load_json(physical_inputs["scenarioConfig"])
    run_passport = _load_json(physical_inputs["runPassport"])
    provider_registry = _load_json(physical_inputs["providers"])
    workflow = _load_json(physical_inputs["workflow"])
    tender_checklist = _load_json(physical_inputs["procurement"])
    repro_manifest = _load_json(physical_inputs["reproManifest"])
    reproduction = _load_json(physical_inputs["reproMetadata"])
    portfolio = _load_json(physical_inputs["portfolioResults"])

    data_requests = _data_requests()
    missing_evidence = _missing_evidence(data_requests)
    pilot_criteria = _pilot_criteria()
    risk_register = _risk_register(dossier, tender_checklist)
    comparison = _scenario_comparison(portfolio)
    data_readiness = _data_readiness(provider_registry, data_requests, missing_evidence, created_at)
    pilot_monitoring = _pilot_monitoring_plan(pilot_criteria, created_at)

    files: dict[str, str] = {}

    files["application_summary_md"] = _write_text(
        output_dir / "application_summary.md",
        _application_summary_markdown(
            dossier=dossier,
            run_passport=run_passport,
            workflow=workflow,
            tender_checklist=tender_checklist,
            data_requests=data_requests,
            missing_evidence=missing_evidence,
            pilot_criteria=pilot_criteria,
        ),
    )
    files["application_summary_html"] = _write_text(
        output_dir / "application_summary.html",
        _markdown_document_to_html(
            "Abay Signal Retiming Application Summary",
            Path(files["application_summary_md"]).read_text(encoding="utf-8"),
        ),
    )
    files["data_request_memo_md"] = _write_text(
        output_dir / "data_request_memo.md",
        _data_request_memo(data_requests),
    )
    files["data_readiness_json"] = _write_json(output_dir / "data_readiness.json", data_readiness)
    files["missing_evidence_json"] = _write_json(
        output_dir / "missing_evidence.json",
        {
            "id": "abay-signal-retiming-missing-evidence",
            "kind": "missing-evidence-list",
            "claimLevel": "demo",
            "createdAt": created_at,
            "currentSafePosition": SAFE_POSITION,
            "items": missing_evidence,
        },
    )
    files["pilot_acceptance_criteria_json"] = _write_json(
        output_dir / "pilot_acceptance_criteria.json",
        {
            "id": "abay-signal-retiming-pilot-acceptance-criteria",
            "kind": "pilot-acceptance-criteria",
            "claimLevel": "demo",
            "createdAt": created_at,
            "criteria": [asdict(criterion) for criterion in pilot_criteria],
            "decisionAfterPilot": ["scale", "revise", "stop", "collect_more_data"],
        },
    )
    files["pilot_monitoring_plan_json"] = _write_json(output_dir / "pilot_monitoring_plan.json", pilot_monitoring)
    files["pilot_monitoring_plan_md"] = _write_text(
        output_dir / "pilot_monitoring_plan.md",
        _pilot_monitoring_markdown(pilot_monitoring),
    )
    files["executive_brief_md"] = _write_text(
        output_dir / "executive_brief.md",
        _executive_brief(dossier, comparison),
    )
    files["demo_script_md"] = _write_text(output_dir / "demo_script.md", _demo_script())
    files["slide_outline_md"] = _write_text(output_dir / "slide_outline.md", _slide_outline())
    files["risk_register_json"] = _write_json(
        output_dir / "risk_register.json",
        {
            "id": "abay-signal-retiming-risk-register",
            "kind": "pilot-risk-register",
            "claimLevel": "demo",
            "createdAt": created_at,
            "risks": [asdict(risk) for risk in risk_register],
        },
    )
    files["scenario_alternative_comparison_json"] = _write_json(
        output_dir / "scenario_alternative_comparison.json",
        {
            "id": "abay-scenario-alternative-comparison",
            "kind": "scenario-alternative-comparison",
            "claimLevel": portfolio.get("claimLevel", "proxy"),
            "createdAt": created_at,
            "alternatives": comparison,
            "limitations": [_sanitize_buyer_text(item) for item in portfolio.get("limitations", [])],
        },
    )
    files["scenario_alternative_comparison_md"] = _write_text(
        output_dir / "scenario_alternative_comparison.md",
        _scenario_comparison_markdown(
            comparison,
            [_sanitize_buyer_text(item) for item in portfolio.get("limitations", [])],
        ),
    )
    files["claim_boundary_md"] = _write_text(output_dir / "claim_boundary.md", _claim_boundary())
    files["local_onprem_deployment_note_md"] = _write_text(
        output_dir / "local_onprem_deployment_note.md",
        _local_onprem_deployment_note(tender_checklist, reproduction),
    )

    source_artifacts = _source_artifacts(physical_inputs, logical_refs)
    generated_artifacts = [
        _artifact_entry(
            Path(path),
            "generated-pack-artifact",
            "demo",
            logical_ref=resolved_output_refs[role],
        )
        for role, path in files.items()
    ]
    evidence_manifest = {
        "id": "abay-signal-retiming-akimat-evidence-manifest",
        "kind": "akimat-evidence-manifest",
        "claimLevel": "demo",
        "createdAt": created_at,
        "currentSafePosition": SAFE_POSITION,
        "sourceArtifacts": source_artifacts,
        "generatedArtifacts": generated_artifacts,
        "claimBoundary": {
            "dossierClaimLevel": dossier.get("claimLevel", "proxy"),
            "applicationPackClaimLevel": "demo",
            "unsupportedClaims": [
                "certified procurement acceptance",
                "real-time municipal feed",
                "calibrated city-wide model",
                "guaranteed congestion reduction",
                "automatic signal control",
                "legally binding approval process",
            ],
        },
    }
    files["evidence_manifest_json"] = _write_json(output_dir / "evidence_manifest.json", evidence_manifest)

    procurement_pack_index = {
        "id": "abay-signal-retiming-procurement-pilot-pack",
        "kind": "akimat-procurement-pilot-pack",
        "claimLevel": "demo",
        "createdAt": created_at,
        "scenarioId": dossier.get("id", "abay-signal-retiming"),
        "dossierClaimLevel": dossier.get("claimLevel", "proxy"),
        "currentSafePosition": SAFE_POSITION,
        "decisionSummary": _decision_summary(dossier),
        "inputs": source_artifacts,
        "outputs": _file_index(files, resolved_output_refs),
        "includedSections": [
            "decision summary",
            "scenario config",
            "dossier JSON and markdown/html summary",
            "KPI CSV and scenario comparison",
            "run passport",
            "provider registry and road provider status",
            "workflow history and artifact locks",
            "reproduction artifact manifest",
            "tender checklist",
            "research appendix when present",
            "missing evidence list",
            "pilot acceptance criteria",
            "claim boundary statement",
        ],
        "apiBoundary": {
            "readExistingPack": "GET /api/exports/procurement-pack",
            "generatePack": "POST /api/exports/procurement-pack",
        },
        "limitations": _pack_limitations(dossier, tender_checklist),
    }
    files["procurement_pack_index_json"] = _write_json(
        output_dir / "procurement_pack_index.json",
        procurement_pack_index,
    )

    application_package_index = {
        "id": "abay-signal-retiming-akimat-application-package",
        "kind": "akimat-application-package-index",
        "claimLevel": "demo",
        "createdAt": created_at,
        "scenarioId": dossier.get("id", "abay-signal-retiming"),
        "currentSafePosition": SAFE_POSITION,
        "recommendedReviewSequence": [
            "application_summary_md",
            "executive_brief_md",
            "scenario_alternative_comparison_md",
            "data_request_memo_md",
            "pilot_monitoring_plan_md",
            "procurement_pack_index_json",
            "claim_boundary_md",
            "demo_script_md",
            "slide_outline_md",
        ],
        "files": _file_index(files, resolved_output_refs),
        "nextAction": "Attach Akimat-provided observed corridor, signal, bus, incident, cost, reviewer, and legal permission evidence before stronger claims.",
    }
    files["application_package_index_json"] = _write_json(
        output_dir / "application_package_index.json",
        application_package_index,
    )

    return {
        "id": application_package_index["id"],
        "claimLevel": application_package_index["claimLevel"],
        "createdAt": created_at,
        "outputDir": str(output_dir),
        "safePosition": SAFE_POSITION,
        "files": files,
        "sourceArtifactCount": len(source_artifacts),
        "generatedArtifactCount": len(files),
        "recommendation": _decision_summary(dossier),
        "limitations": _pack_limitations(dossier, tender_checklist),
    }


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    return str(path)


def _write_text(path: Path, content: str) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.rstrip() + "\n", encoding="utf-8")
    return str(path)


def _sha256(path: Path) -> str | None:
    if not path.exists():
        return None
    return sha256(path.read_bytes()).hexdigest()


def _artifact_entry(
    path: Path,
    kind: str,
    claim_level: str,
    required: bool = True,
    *,
    logical_ref: str | None = None,
) -> dict[str, Any]:
    exists = path.exists()
    return {
        "kind": kind,
        "path": logical_ref if logical_ref is not None else str(path),
        "claimLevel": claim_level,
        "required": required,
        "available": exists,
        "bytes": path.stat().st_size if exists else None,
        "sha256": _sha256(path),
    }


def _source_artifacts(
    physical_inputs: Mapping[str, Path],
    logical_refs: Mapping[str, str],
) -> list[dict[str, Any]]:
    metadata = {
        "scenarioConfig": ("scenario-config", "demo", True),
        "dossier": ("scenario-dossier-json", "proxy", True),
        "dossierMarkdown": ("scenario-dossier-markdown", "proxy", False),
        "runPassport": ("run-passport", "demo", True),
        "providers": ("provider-registry", "demo", True),
        "roadsProviderStatus": ("road-provider-status", "real-data", True),
        "workflow": ("workflow-custody", "demo", True),
        "procurement": ("tender-checklist", "demo", True),
        "reproManifest": ("reproduction-artifact-manifest", "demo", True),
        "reproMetadata": ("reproduction-metadata", "demo", True),
        "portfolioResults": ("scenario-portfolio-json", "proxy", True),
        "portfolioMatrix": ("scenario-portfolio-kpi-csv", "proxy", True),
        "researchAppendix": ("research-appendix", "demo", False),
    }
    ordered_roles = tuple(REQUIRED_INPUT_PATHS) + tuple(OPTIONAL_INPUT_PATHS)
    return [
        _artifact_entry(
            physical_inputs[role],
            metadata[role][0],
            metadata[role][1],
            metadata[role][2],
            logical_ref=logical_refs[role],
        )
        for role in ordered_roles
        if role in physical_inputs
    ]


def _resolve_input_context(
    inputs: Mapping[str, str | Path] | None,
    evidence_refs: Mapping[str, str] | None,
) -> tuple[dict[str, Path], dict[str, str]]:
    if inputs is None:
        if evidence_refs is not None:
            raise ValueError("inputs is required when evidence_refs is explicit")
        physical = dict(REQUIRED_INPUT_PATHS) | dict(OPTIONAL_INPUT_PATHS)
        return physical, {role: str(path) for role, path in physical.items()}

    required = set(REQUIRED_INPUT_PATHS)
    allowed = required | set(OPTIONAL_INPUT_PATHS)
    actual = set(inputs)
    missing = sorted(required - actual)
    unknown = sorted(actual - allowed)
    if missing or unknown:
        raise ValueError(f"Invalid inputs: missing={missing}, unknown={unknown}")
    if evidence_refs is None:
        raise ValueError("evidence_refs is required when inputs is explicit")
    _require_exact_roles(evidence_refs, actual, map_name="evidence_refs")
    physical = {role: Path(inputs[role]) for role in inputs}
    refs = {
        role: _logical_ref(evidence_refs[role], role=role)
        for role in inputs
    }
    return physical, refs


def _resolve_output_refs(
    output_dir: Path,
    output_refs: Mapping[str, str] | None,
    *,
    explicit: bool,
) -> dict[str, str]:
    filenames = {
        "application_summary_md": "application_summary.md",
        "application_summary_html": "application_summary.html",
        "data_request_memo_md": "data_request_memo.md",
        "data_readiness_json": "data_readiness.json",
        "missing_evidence_json": "missing_evidence.json",
        "pilot_acceptance_criteria_json": "pilot_acceptance_criteria.json",
        "pilot_monitoring_plan_json": "pilot_monitoring_plan.json",
        "pilot_monitoring_plan_md": "pilot_monitoring_plan.md",
        "executive_brief_md": "executive_brief.md",
        "demo_script_md": "demo_script.md",
        "slide_outline_md": "slide_outline.md",
        "risk_register_json": "risk_register.json",
        "scenario_alternative_comparison_json": "scenario_alternative_comparison.json",
        "scenario_alternative_comparison_md": "scenario_alternative_comparison.md",
        "claim_boundary_md": "claim_boundary.md",
        "local_onprem_deployment_note_md": "local_onprem_deployment_note.md",
        "evidence_manifest_json": "evidence_manifest.json",
        "procurement_pack_index_json": "procurement_pack_index.json",
        "application_package_index_json": "application_package_index.json",
    }
    if tuple(filenames) != GENERATED_FILE_ROLES:
        raise RuntimeError("Akimat generated-file role registry is inconsistent")
    if output_refs is None:
        if explicit:
            raise ValueError("output_refs is required when inputs is explicit")
        return {role: str(output_dir / filename) for role, filename in filenames.items()}
    _require_exact_roles(output_refs, set(GENERATED_FILE_ROLES), map_name="output_refs")
    return {
        role: _logical_ref(output_refs[role], role=role)
        for role in GENERATED_FILE_ROLES
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


def _file_index(
    files: dict[str, str],
    output_refs: Mapping[str, str],
) -> list[dict[str, Any]]:
    return [
        _artifact_entry(
            Path(path),
            role.replace("_", "-"),
            "demo",
            logical_ref=output_refs[role],
        )
        | {"role": role}
        for role, path in sorted(files.items())
    ]


def _data_requests() -> list[AkimatDataRequest]:
    return [
        AkimatDataRequest(
            id="observed-corridor-speed-counts",
            dataset="Observed corridor speed or detector counts",
            requested_owner="Akimat traffic data steward",
            why_needed="Validate modeled speed, queue, and person-hour deltas for the Abay corridor.",
            minimum_format="CSV by segment and 15-minute interval, including collection date, direction, and method.",
            current_claim_level="proxy",
            claim_upgrade_use="Required input for calibrated KPI review.",
        ),
        AkimatDataRequest(
            id="bus-travel-time-reliability",
            dataset="Public transport travel time and reliability",
            requested_owner="Public transport operator or Onay data steward",
            why_needed="Replace the bus reliability proxy with observed service impact.",
            minimum_format="Route, stop pair, timestamp, scheduled time, observed time, and headway if available.",
            current_claim_level="proxy",
            claim_upgrade_use="Supports calibrated public transport KPI review.",
        ),
        AkimatDataRequest(
            id="current-signal-timing-plan",
            dataset="Current signal timing plan and controller constraints",
            requested_owner="Signal engineering lead",
            why_needed="Check whether the retiming scenario is operationally feasible and safe.",
            minimum_format="Phase table, cycle length, offsets, pedestrian constraints, and approval notes.",
            current_claim_level="proxy",
            claim_upgrade_use="Turns the measure into an engineer-reviewed scenario input.",
        ),
        AkimatDataRequest(
            id="incident-roadwork-history",
            dataset="Incident and roadwork history",
            requested_owner="Operations dispatcher or police liaison",
            why_needed="Separate recurring congestion from incident-driven outliers in baseline windows.",
            minimum_format="Timestamped events with location, duration, severity, and closure notes.",
            current_claim_level="proxy",
            claim_upgrade_use="Improves calibration review and pilot monitoring design.",
        ),
        AkimatDataRequest(
            id="capex-opex-estimates",
            dataset="CAPEX and OPEX estimates",
            requested_owner="Finance or engineering cost reviewer",
            why_needed="Replace placeholders in ROI, payback, and budget movement calculations.",
            minimum_format="Line-item estimate with source, date, assumptions, and review owner.",
            current_claim_level="proxy",
            claim_upgrade_use="Required before budget language can be strengthened.",
        ),
        AkimatDataRequest(
            id="nominated-reviewer-data-steward",
            dataset="Nominated reviewer and data steward",
            requested_owner="Akimat sponsor",
            why_needed="Bind evidence review, data access, and workflow custody to named municipal owners.",
            minimum_format="Name, role, department, review responsibility, and contact channel.",
            current_claim_level="demo",
            claim_upgrade_use="Needed for signed workflow custody and pilot acceptance evidence.",
        ),
        AkimatDataRequest(
            id="legal-feed-permissions",
            dataset="Legal permission for feeds and derived artifacts",
            requested_owner="Legal or data governance reviewer",
            why_needed="Confirm permitted use of municipal feeds, OSM-derived geometry, and generated reports.",
            minimum_format="Written permission scope, allowed storage location, retention rule, and publication limits.",
            current_claim_level="demo",
            claim_upgrade_use="Needed before any externally distributed buyer package uses restricted feeds.",
        ),
    ]


def _missing_evidence(requests: list[AkimatDataRequest]) -> list[dict[str, Any]]:
    return [
        {
            "id": request.id,
            "dataset": request.dataset,
            "currentClaimLevel": request.current_claim_level,
            "blocks": request.claim_upgrade_use,
            "requestedOwner": request.requested_owner,
            "minimumFormat": request.minimum_format,
            "status": "missing-from-akimat",
        }
        for request in requests
    ]


def _pilot_criteria() -> list[PilotCriterion]:
    baseline_window = "10 comparable weekdays before intervention, excluding documented incidents and holidays."
    pilot_window = "10 comparable weekdays after stabilization, using the same time bands and corridor segments."
    return [
        PilotCriterion(
            id="person-hours-forecast-vs-fact",
            kpi_id="person_hours_saved",
            owner="transport planning reviewer",
            data_source="observed corridor speed/count dataset plus vehicle occupancy assumption register",
            baseline_window=baseline_window,
            pilot_window=pilot_window,
            acceptable_threshold="Forecast-vs-fact absolute error at or below 20 percent, or documented reason for recalibration.",
            recalibration_trigger="Observed sign or magnitude conflicts with proxy forecast for two consecutive review windows.",
            decision_use="scale if benefit direction is confirmed and safety/cost gates remain acceptable; revise or collect_more_data otherwise.",
            current_claim_level="proxy",
        ),
        PilotCriterion(
            id="corridor-speed-forecast-vs-fact",
            kpi_id="corridor_speed_delta",
            owner="traffic engineering reviewer",
            data_source="observed speed by corridor segment and direction",
            baseline_window=baseline_window,
            pilot_window=pilot_window,
            acceptable_threshold="Measured peak-period delta remains within +/- 1.0 km/h or 25 percent of the forecast magnitude, whichever is larger.",
            recalibration_trigger="Measured speed decreases on the target corridor without incident explanation.",
            decision_use="revise timing plan if corridor speed or queue evidence contradicts forecast.",
            current_claim_level="proxy",
        ),
        PilotCriterion(
            id="bus-reliability-forecast-vs-fact",
            kpi_id="bus_reliability_proxy",
            owner="public transport reviewer",
            data_source="bus travel time, schedule adherence, and headway reliability records",
            baseline_window=baseline_window,
            pilot_window=pilot_window,
            acceptable_threshold="Observed reliability direction is non-negative for affected routes, or mitigation is documented.",
            recalibration_trigger="Bus reliability worsens for two consecutive review windows.",
            decision_use="stop or revise if bus reliability worsens without offsetting public benefit.",
            current_claim_level="proxy",
        ),
        PilotCriterion(
            id="cost-placeholder-replacement",
            kpi_id="capex_placeholder",
            owner="finance or engineering cost reviewer",
            data_source="line-item CAPEX/OPEX estimate and implementation invoice records",
            baseline_window="Before funding decision.",
            pilot_window="Before scale decision.",
            acceptable_threshold="Cost record replaces placeholders and includes source, date, reviewer, and confidence note.",
            recalibration_trigger="Cost changes ROI/payback sign or materially changes affordability.",
            decision_use="defer or revise if sourced cost invalidates the conditional case.",
            current_claim_level="proxy",
        ),
    ]


def _risk_register(dossier: dict[str, Any], tender_checklist: dict[str, Any]) -> list[RiskItem]:
    risks = [
        RiskItem(
            id="claim-overreach",
            area="governance",
            risk="Decision users may overread proxy KPIs as implementation evidence.",
            severity="high",
            mitigation="Keep claim badges, allowed actions, limitations, and missing evidence in every UI/export surface.",
            evidence_needed="Observed speed/count, signal, bus, cost, reviewer, and permission evidence.",
            claim_level="demo",
        ),
        RiskItem(
            id="signal-feasibility",
            area="engineering",
            risk="Retiming assumptions may conflict with controller constraints, pedestrian timing, or adjacent intersection coordination.",
            severity="high",
            mitigation="Require signal engineering review before conditional funding moves to implementation.",
            evidence_needed="Current signal plan, controller constraints, and engineer sign-off.",
            claim_level="proxy",
        ),
        RiskItem(
            id="cost-placeholders",
            area="commercial",
            risk="ROI and payback remain placeholder-sensitive.",
            severity="medium",
            mitigation="Separate technical pilot value from budget decision until sourced CAPEX/OPEX is attached.",
            evidence_needed="Line-item CAPEX/OPEX estimate with reviewer and source.",
            claim_level="proxy",
        ),
        RiskItem(
            id="data-access-delay",
            area="data",
            risk="Akimat data access delays could prevent calibration before a pilot decision window.",
            severity="medium",
            mitigation="Use the data request memo as a gating checklist and nominate a data steward.",
            evidence_needed="Named data steward and legal permission for feeds.",
            claim_level="demo",
        ),
    ]
    for index, text in enumerate(dossier.get("risks", []), start=1):
        risks.append(
            RiskItem(
                id=f"dossier-risk-{index}",
                area="dossier",
                risk=str(text),
                severity="medium",
                mitigation="Track in the workbench limitation/risk list until Akimat evidence is attached.",
                evidence_needed="See missing evidence list.",
                claim_level=str(dossier.get("claimLevel", "proxy")),
            )
        )
    if tender_checklist.get("limitations"):
        risks.append(
            RiskItem(
                id="procurement-control-gaps",
                area="procurement",
                risk="Procurement controls remain file-based and not yet backed by signed enterprise controls.",
                severity="high",
                mitigation="Use checklist gaps as pilot conditions, not final acceptance evidence.",
                evidence_needed="Signed security, SLA, legal, training, and acceptance records.",
                claim_level=str(tender_checklist.get("claimLevel", "demo")),
            )
        )
    return risks


def _scenario_comparison(portfolio: dict[str, Any]) -> list[dict[str, Any]]:
    baseline = portfolio.get("baseline", {})
    alternatives: list[dict[str, Any]] = [
        {
            "rank": 0,
            "scenarioId": "no-build-baseline",
            "scenarioName": baseline.get("label", "No-build baseline"),
            "scenarioType": "baseline",
            "effect": "Reference case; no intervention effect.",
            "costPlaceholderKzt": 0,
            "confidence": "reference",
            "claimLevel": "proxy",
            "readiness": "baseline-only",
            "openDossierPath": None,
            "reasonNotStronger": "Baseline still uses proxy analytics until observed corridor evidence is attached.",
        }
    ]
    for row in portfolio.get("matrix", []):
        scenario_id = row.get("scenario_id")
        reasons = [
            "Observed traffic, bus, queue, incident, and cost evidence is not attached.",
            "Cost values are placeholders until reviewed by Akimat or engineering finance.",
        ]
        alternatives.append(
            {
                "rank": row.get("rank"),
                "scenarioId": scenario_id,
                "scenarioName": row.get("scenario_name"),
                "scenarioType": row.get("scenario_type"),
                "effect": (
                    f"{_fmt(row.get('person_hours_saved', 0))} person-hours saved, "
                    f"{_fmt(row.get('corridor_speed_delta', 0))} km/h speed delta, "
                    f"{_fmt(row.get('bus_reliability_proxy', 0))}% bus reliability proxy."
                ),
                "costPlaceholderKzt": row.get("capex_placeholder"),
                "confidence": row.get("decision_signal"),
                "claimLevel": row.get("claim_level", "proxy"),
                "readiness": "dossier-linked" if scenario_id == "abay-signal-retiming" else "portfolio-screened",
                "openDossierPath": "/scenarios/abay-signal-retiming/dossier" if scenario_id == "abay-signal-retiming" else None,
                "reasonNotStronger": " ".join(reasons),
            }
        )
    return alternatives


def _data_readiness(
    registry: dict[str, Any],
    requests: list[AkimatDataRequest],
    missing_evidence: list[dict[str, Any]],
    created_at: str,
) -> dict[str, Any]:
    providers = registry.get("providers", [])
    groups: dict[str, list[dict[str, Any]]] = {
        "real-data": [],
        "proxy": [],
        "demo": [],
        "missing": [],
    }
    for provider in providers:
        claim = provider.get("claim_label") or provider.get("claimLevel") or "demo"
        bucket = "missing" if not provider.get("available") else str(claim)
        groups.setdefault(bucket, []).append(
            {
                "id": provider.get("id"),
                "label": provider.get("label"),
                "path": provider.get("path"),
                "claimLevel": claim,
                "available": provider.get("available", False),
                "limitations": provider.get("limitations", []),
            }
        )
    return {
        "id": "abay-signal-retiming-data-readiness",
        "kind": "akimat-data-readiness",
        "claimLevel": "demo",
        "createdAt": created_at,
        "currentSafePosition": SAFE_POSITION,
        "providerSummary": registry.get("summary", {}),
        "providerGroups": groups,
        "akimatRequests": [asdict(request) for request in requests],
        "missingEvidence": missing_evidence,
        "upgradeRule": "Only attached, reviewable Akimat evidence can move KPI language from proxy toward calibrated.",
    }


def _pilot_monitoring_plan(criteria: list[PilotCriterion], created_at: str) -> dict[str, Any]:
    return {
        "id": "abay-signal-retiming-pilot-monitoring-plan",
        "kind": "forecast-vs-fact-pilot-monitoring-plan",
        "claimLevel": "demo",
        "createdAt": created_at,
        "baselineMeasurementWindow": "10 comparable weekdays before intervention, same peak windows and corridor segments.",
        "pilotMeasurementWindow": "10 comparable weekdays after stabilization, same peak windows and corridor segments.",
        "forecastVsFactTemplate": [
            {
                "kpiId": criterion.kpi_id,
                "forecastValue": None,
                "observedBaseline": None,
                "observedPilot": None,
                "observedDelta": None,
                "absoluteError": None,
                "reviewer": criterion.owner,
                "decisionNote": None,
            }
            for criterion in criteria
        ],
        "criteria": [asdict(criterion) for criterion in criteria],
        "reviewCadence": [
            "pre-pilot evidence readiness review",
            "week 1 operational safety check",
            "end-of-window forecast-vs-fact review",
            "scale/revise/stop/collect_more_data decision",
        ],
        "decisionAfterPilot": ["scale", "revise", "stop", "collect_more_data"],
        "recalibrationPolicy": "Recalibrate if observed direction or magnitude conflicts with proxy forecast under documented comparable conditions.",
    }


def _decision_summary(dossier: dict[str, Any]) -> dict[str, Any]:
    recommendation = dossier.get("recommendation", {})
    return {
        "decision": recommendation.get("decision"),
        "rationale": recommendation.get("rationale"),
        "allowedDecisions": recommendation.get("allowedDecisions", []),
        "claimLevel": recommendation.get("claimLevel", dossier.get("claimLevel", "proxy")),
    }


def _pack_limitations(dossier: dict[str, Any], tender_checklist: dict[str, Any]) -> list[str]:
    limitations = [
        "This is a pilot/application evidence pack assembled from existing proxy and demo artifacts.",
        "It does not replace municipal engineering, legal, security, finance, or procurement review.",
    ]
    limitations.extend(str(item) for item in dossier.get("limitations", []))
    limitations.extend(str(item) for item in tender_checklist.get("limitations", []))
    return list(dict.fromkeys(limitations))


def _application_summary_markdown(
    dossier: dict[str, Any],
    run_passport: dict[str, Any],
    workflow: dict[str, Any],
    tender_checklist: dict[str, Any],
    data_requests: list[AkimatDataRequest],
    missing_evidence: list[dict[str, Any]],
    pilot_criteria: list[PilotCriterion],
) -> str:
    recommendation = _decision_summary(dossier)
    kpis = dossier.get("executiveKpis", {}).get("kpis", [])
    kpi_lines = "\n".join(
        f"- {kpi.get('label')}: baseline {kpi.get('baseline')} {kpi.get('unit')}, "
        f"measure {kpi.get('measure')} {kpi.get('unit')}, delta {kpi.get('delta')} "
        f"({kpi.get('claimLevel')})."
        for kpi in kpis[:6]
    )
    request_lines = "\n".join(
        f"- {request.dataset}: {request.minimum_format}" for request in data_requests
    )
    return f"""
# Abay Signal Retiming Akimat Application Summary

## Current safe position

{SAFE_POSITION}

## Decision file

- Corridor: {dossier.get("corridor", {}).get("name", "Abay corridor")}
- Proposed measure: {dossier.get("proposedMeasure", {}).get("label", "signal retiming")}
- Decision question: {dossier.get("decisionQuestion")}
- Current recommendation: {recommendation.get("decision")}
- Current claim level: {dossier.get("claimLevel", "proxy")}
- Run ID: {run_passport.get("runId", "not recorded")}
- Workflow status: {workflow.get("status", "not recorded")}
- Tender checklist claim level: {tender_checklist.get("claimLevel", "demo")}

## KPI evidence snapshot

{kpi_lines}

## Allowed decision posture

Allowed actions are limited to investigate further, defer, fund conditional on evidence, or reject while the dossier remains proxy-level.

## Evidence required from Akimat

{request_lines}

## Missing evidence count

{len(missing_evidence)} evidence groups are still missing from the municipal side.

## Pilot acceptance frame

The pilot must compare forecast and observed facts using {len(pilot_criteria)} KPI criteria. The post-pilot decision is scale, revise, stop, or collect_more_data.
"""


def _data_request_memo(requests: list[AkimatDataRequest]) -> str:
    lines = [
        "# Abay Signal Retiming Data Request Memo",
        "",
        "Purpose: collect the minimum municipal evidence needed to review the proxy dossier under a calibrated pilot decision process.",
        "",
    ]
    for request in requests:
        lines.extend(
            [
                f"## {request.dataset}",
                "",
                f"- Requested owner: {request.requested_owner}",
                f"- Why needed: {request.why_needed}",
                f"- Minimum format: {request.minimum_format}",
                f"- Current claim level: {request.current_claim_level}",
                f"- Claim upgrade use: {request.claim_upgrade_use}",
                "",
            ]
        )
    return "\n".join(lines)


def _pilot_monitoring_markdown(plan: dict[str, Any]) -> str:
    criteria = "\n".join(
        f"- {item['kpi_id']}: owner {item['owner']}; source {item['data_source']}; threshold {item['acceptable_threshold']}"
        for item in plan["criteria"]
    )
    return f"""
# Abay Signal Retiming Pilot Monitoring Plan

## Measurement windows

- Baseline: {plan["baselineMeasurementWindow"]}
- Pilot: {plan["pilotMeasurementWindow"]}

## KPI criteria

{criteria}

## Forecast-vs-fact template

Each KPI review records forecast value, observed baseline, observed pilot, observed delta, absolute error, reviewer, and decision note.

## Decision after pilot

Allowed post-pilot decisions: {", ".join(plan["decisionAfterPilot"])}.

## Recalibration trigger

{plan["recalibrationPolicy"]}
"""


def _executive_brief(dossier: dict[str, Any], comparison: list[dict[str, Any]]) -> str:
    recommendation = _decision_summary(dossier)
    top_alternative = next((item for item in comparison if item.get("scenarioId") == "abay-signal-retiming"), comparison[0])
    return f"""
# Executive Brief: Abay Signal Retiming Pilot Case

## Ask

Authorize an evidence-gated review of the Abay signal retiming pilot case and provide the missing municipal datasets listed in the data request memo.

## Current result

{SAFE_POSITION}

## Recommended posture

- Decision: {recommendation.get("decision")}
- Rationale: {recommendation.get("rationale")}
- Claim level: {recommendation.get("claimLevel")}

## Alternative comparison

Top dossier-linked option: {top_alternative.get("scenarioName")} with {top_alternative.get("effect")}

## Why this is not a clean funding decision yet

The dossier uses proxy KPI evidence, placeholder cost inputs, and file-based workflow custody. The next decision should be conditional on observed corridor, public transport, signal timing, incident, cost, reviewer, and legal permission evidence.
"""


def _demo_script() -> str:
    return """
# Akimat Demo Script

1. Open `/scenarios/abay-signal-retiming/dossier`.
2. Start with the decision question, recommendation, current claim badge, and allowed actions.
3. Review KPI deltas and point out formulas, placeholder flags, and claim labels.
4. Open the run passport and show seed, model version or git hash, scenario params, sources, limitations, and reproduction path.
5. Review data readiness and the Akimat data request memo.
6. Review workflow custody, artifact locks, owners, hashes, and next action.
7. Review procurement gaps and the application package export index.
8. Close on the pilot monitoring plan: forecast-vs-fact, recalibration trigger, and scale/revise/stop/collect_more_data decision.
"""


def _slide_outline() -> str:
    return """
# 9-Slide Akimat Application Outline

1. Abay corridor pilot case and decision question.
2. Scenario chain: config, run metadata, KPI JSON, dossier, evidence pack.
3. Baseline vs measure KPI delta table with claim labels.
4. Alternative comparison: no-build, signal retiming, bus priority, repair detour/capacity reduction.
5. Evidence gate: allowed actions and blocked claims.
6. Data readiness and Akimat data request.
7. Workflow custody and reproducibility evidence.
8. Procurement and local/on-prem deployment gaps.
9. Pilot monitoring plan and forecast-vs-fact decision after pilot.
"""


def _scenario_comparison_markdown(comparison: list[dict[str, Any]], limitations: list[str]) -> str:
    rows = [
        "| Rank | Scenario | Effect | Cost placeholder KZT | Claim | Readiness | Reason not stronger |",
        "| --- | --- | --- | ---: | --- | --- | --- |",
    ]
    for item in comparison:
        rows.append(
            "| {rank} | {name} | {effect} | {cost} | {claim} | {readiness} | {reason} |".format(
                rank=item.get("rank"),
                name=item.get("scenarioName"),
                effect=item.get("effect"),
                cost=item.get("costPlaceholderKzt") or 0,
                claim=item.get("claimLevel"),
                readiness=item.get("readiness"),
                reason=item.get("reasonNotStronger"),
            )
        )
    limitation_lines = "\n".join(f"- {item}" for item in limitations)
    return f"""
# Abay Scenario Alternative Comparison

{chr(10).join(rows)}

## Portfolio limitations

{limitation_lines}
"""


def _claim_boundary() -> str:
    return f"""
# Claim Boundary Statement

## Current safe position

{SAFE_POSITION}

## Current labels

- Application pack: demo
- Dossier and KPI deltas: proxy
- Cached road geometry snapshot: real-data

## Statements this package does not make

- It does not claim certified procurement acceptance.
- It does not claim a real-time municipal traffic feed.
- It does not claim a calibrated city-wide model.
- It does not claim guaranteed congestion reduction.
- It does not claim automatic signal control.
- It does not claim a legally binding approval process.

## Upgrade rule

Claim labels can change only after attaching reviewable evidence and updating the Claim Ledger.
"""


def _local_onprem_deployment_note(tender_checklist: dict[str, Any], reproduction: dict[str, Any]) -> str:
    run_path = tender_checklist.get("localOnPremRunPath", [])
    commands = "\n".join(f"```bash\n{command}\n```" for command in run_path)
    repro_commands = "\n".join(
        " ".join(command.get("command", [])) for command in reproduction.get("commands", [])
    )
    return f"""
# Local / On-Prem Deployment Note

## Current posture

The repository supports local generation of the dossier and application evidence pack. It has not been hardened, scanned, or deployed in a municipal production environment.

## Tender checklist run path

{commands}

## Reproduction commands captured in metadata

```bash
{repro_commands}
```

## Remaining controls

- Container image scan and dependency review.
- Kazakhstan-controlled storage and retention policy.
- Authenticated roles, SSO/RBAC, and append-only audit storage.
- Backup/restore drill and operational SLA.
- Signed legal and security review.
"""


def _markdown_document_to_html(title: str, markdown: str) -> str:
    body_lines: list[str] = []
    in_list = False
    in_code = False
    for raw_line in markdown.splitlines():
        line = raw_line.rstrip()
        if line.startswith("```"):
            if in_code:
                body_lines.append("</code></pre>")
                in_code = False
            else:
                if in_list:
                    body_lines.append("</ul>")
                    in_list = False
                body_lines.append("<pre><code>")
                in_code = True
            continue
        if in_code:
            body_lines.append(escape(line))
            continue
        if not line:
            if in_list:
                body_lines.append("</ul>")
                in_list = False
            continue
        if line.startswith("# "):
            if in_list:
                body_lines.append("</ul>")
                in_list = False
            body_lines.append(f"<h1>{escape(line[2:])}</h1>")
        elif line.startswith("## "):
            if in_list:
                body_lines.append("</ul>")
                in_list = False
            body_lines.append(f"<h2>{escape(line[3:])}</h2>")
        elif line.startswith("- "):
            if not in_list:
                body_lines.append("<ul>")
                in_list = True
            body_lines.append(f"<li>{escape(line[2:])}</li>")
        else:
            if in_list:
                body_lines.append("</ul>")
                in_list = False
            body_lines.append(f"<p>{escape(line)}</p>")
    if in_list:
        body_lines.append("</ul>")
    if in_code:
        body_lines.append("</code></pre>")

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{escape(title)}</title>
  <style>
    body {{ margin: 0; background: #f7f5ef; color: #1f211d; font: 15px/1.55 Arial, sans-serif; }}
    main {{ max-width: 960px; margin: 0 auto; padding: 40px 28px; }}
    h1, h2 {{ line-height: 1.15; }}
    h1 {{ font-size: 32px; margin: 0 0 28px; }}
    h2 {{ font-size: 18px; margin: 28px 0 10px; border-top: 1px solid #cfc8bb; padding-top: 18px; }}
    p, li {{ max-width: 78ch; }}
    ul {{ padding-left: 22px; }}
    pre {{ background: #ece7dc; padding: 14px; overflow: auto; }}
  </style>
</head>
<body>
  <main>
    {chr(10).join(body_lines)}
  </main>
</body>
</html>
"""


def _fmt(value: Any) -> str:
    try:
        return f"{float(value):,.3f}".rstrip("0").rstrip(".")
    except (TypeError, ValueError):
        return str(value)


def _sanitize_buyer_text(value: Any) -> str:
    text = str(value)
    replacements = {
        "procurement" + "-ready": "stronger procurement",
        "live city " + "feed": "real-time municipal feed",
        "live city " + "data": "real-time municipal data",
        "autonomous traffic " + "control": "automatic signal control",
        "legal approval " + "workflow": "legally binding approval process",
        "guaranteed " + "improvement": "unverified improvement",
        "AI " + "proves": "the model indicates",
    }
    for source, target in replacements.items():
        text = text.replace(source, target)
    return text
