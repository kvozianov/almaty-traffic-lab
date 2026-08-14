from __future__ import annotations

from datetime import datetime, timezone
import csv
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from typing import Any

from .config import ReproductionConfig, load_reproduction_config
from .contracts import canonical_json, validate_paired_experiment_result
from .data_sources import write_provider_registry
from .dossier import generate_scenario_dossier
from .paired_experiment import generate_and_write_abay_signal_pair
from .procurement import generate_procurement_packet
from .research_metrics import generate_research_metrics_pack
from .run_metadata import default_data_sources
from .workflow import generate_decision_workflow


def generate_reproduction_run(
    config_path: str | Path = "simulation.config.json",
    *,
    out_dir: str | Path | None = None,
    prepared_pair_outputs: dict[str, str] | None = None,
    release_run_id: str | None = None,
    paired_experiment_schema_path: str | Path | None = None,
) -> dict[str, Any]:
    config = load_reproduction_config(config_path)
    selected_run_id = release_run_id or config.id
    output_dir = Path(out_dir or config.output_root)
    output_dir.mkdir(parents=True, exist_ok=True)

    commands, pair_outputs, pair_result = _prepare_pair(
        config,
        output_dir,
        prepared_pair_outputs=prepared_pair_outputs,
        schema_path=paired_experiment_schema_path,
    )
    provider_registry = write_provider_registry(output_dir / "data_sources")
    scenario_config_path = _write_reproduction_scenario_config(
        config,
        output_dir,
        provider_registry,
        pair_outputs=pair_outputs,
        release_run_id=selected_run_id,
    )
    dossier = generate_scenario_dossier(
        scenario_config_path,
        release_run_id=selected_run_id,
        paired_experiment_schema_path=paired_experiment_schema_path,
    )
    dossier_paths = {
        "json": str(output_dir / "dossier" / "dossier.json"),
        "markdown": str(output_dir / "dossier" / "dossier.md"),
        "html": str(output_dir / "dossier" / "dossier.html"),
        "kpisCsv": str(output_dir / "dossier" / "kpis.csv"),
    }
    trajectory_path = _write_trajectory_csv(config, output_dir, pair_outputs=pair_outputs)
    kpi_matrix_path = _write_reproduction_kpi_matrix(dossier, output_dir)
    workflow_artifact_paths = {
        "dossierJson": dossier_paths["json"],
        "dossierMarkdown": dossier_paths["markdown"],
        "dossierHtml": dossier_paths["html"],
        "kpiCsv": dossier_paths["kpisCsv"],
        "runPassport": str(output_dir / "run-passport.json"),
    }
    workflow_artifact_refs = {
        "dossierJson": "dossier/dossier.json",
        "dossierMarkdown": "dossier/dossier.md",
        "dossierHtml": "dossier/dossier.html",
        "kpiCsv": "dossier/kpis.csv",
        "runPassport": "run-passport.json",
        "workflowJson": "workflows/abay-signal-retiming-decision-workflow.json",
        "engineerTasksCsv": "workflows/abay-signal-retiming-decision-workflow-engineer-tasks.csv",
        "monitoringJson": "workflows/abay-signal-retiming-decision-workflow-monitoring.json",
        "postAuditJson": "workflows/abay-signal-retiming-decision-workflow-post-audit.json",
        "claimLedger": "docs/obsidian/03-registries/Claim Ledger.md",
    }
    workflow = generate_decision_workflow(
        dossier_paths["json"],
        out_dir=output_dir / "workflows",
        dossier=dossier,
        artifact_paths=workflow_artifact_paths,
        artifact_refs=workflow_artifact_refs,
    )
    workflow_paths = {
        "workflowJson": str(output_dir / "workflows" / "abay-signal-retiming-decision-workflow.json"),
        "engineerTasksCsv": str(output_dir / "workflows" / "abay-signal-retiming-decision-workflow-engineer-tasks.csv"),
        "monitoringJson": str(output_dir / "workflows" / "abay-signal-retiming-decision-workflow-monitoring.json"),
        "postAuditJson": str(output_dir / "workflows" / "abay-signal-retiming-decision-workflow-post-audit.json"),
    }
    procurement = generate_procurement_packet(output_dir / "procurement")
    research_pack = generate_research_metrics_pack(
        dossier_path=dossier_paths["json"],
        portfolio_matrix_path=kpi_matrix_path,
        out_dir=output_dir / "research_metrics",
    )

    generated_paths = _collect_generated_paths(
        scenario_config_path=scenario_config_path,
        config=config,
        provider_registry=provider_registry,
        dossier=dossier,
        trajectory_path=trajectory_path,
        kpi_matrix_path=kpi_matrix_path,
        workflow=workflow,
        procurement=procurement,
        research_pack=research_pack,
        pair_outputs=pair_outputs,
        dossier_paths=dossier_paths,
        workflow_paths=workflow_paths,
    )
    manifest_path = output_dir / "artifact_manifest.json"
    manifest = _artifact_manifest(generated_paths, run_id=selected_run_id)
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=True), encoding="utf-8")

    metadata_path = output_dir / "metadata.json"
    metadata = {
        "id": config.id,
        "kind": "first-epic-reproduction",
        "claimLevel": config.claim_level,
        "releaseRunId": selected_run_id,
        "createdAt": _now(),
        "seed": config.seed,
        "configPath": str(config_path),
        "scenarioConfigPath": str(scenario_config_path),
        "sourceControl": _source_control_status(),
        "inputFingerprints": _input_fingerprints(
            [
                Path(config_path),
                Path(config.paired_experiment.source_analytics_path),
                Path(config.paired_experiment.aggregate_demand_path),
                Path(config.paired_experiment.context_network_path),
                scenario_config_path,
            ]
        ),
        "commands": commands,
        "pairedExperiment": {
            "schemaVersion": pair_result["schemaVersion"],
            "modelId": pair_result["modelId"],
            "semanticFingerprint": pair_result["semanticFingerprint"],
            "controlledDifferences": pair_result["experiment"]["controlledDifferences"],
            "demandControl": pair_result["experiment"]["demandControl"],
            "baseSeriesFingerprint": pair_result["experiment"]["baseSeriesFingerprint"],
            "contextNetworkFingerprint": pair_result["experiment"]["contextNetworkFingerprint"],
            "outputs": pair_outputs,
        },
        "outputs": {
            "metadata": str(metadata_path),
            "artifactManifest": str(manifest_path),
            "trajectoryCsv": str(trajectory_path),
            "kpiMatrix": str(kpi_matrix_path),
            "dossier": dossier_paths,
            "runPassport": str(output_dir / "run-passport.json"),
            "workflow": workflow_paths,
            "procurement": procurement["outputs"],
            "researchMetrics": research_pack["outputs"],
            "providerRegistry": provider_registry["outputs"],
            "pairedExperiment": pair_outputs,
        },
        "artifactCount": len(manifest["artifacts"]),
        "reproducibilityNotes": [
            "Seed and the complete aggregate demand control are identical in baseline and measure.",
            "Baseline 36s and measure 32s variants are regenerated from one source analytics snapshot; only signal delay is controlled.",
            "Run timestamps and git hash may differ between machines; generated KPI and trajectory values are deterministic for the same seed and inputs.",
            "Trajectory CSV is an hourly analytics trajectory export, not raw GPS or vehicle probe traces.",
            "Docker Compose is documented as a prototype path; Docker is not required for this local reproduction command.",
        ],
        "claimLabels": {
            "reproduction": config.claim_level,
            "dossier": dossier.get("claimLevel", "proxy"),
            "researchMetrics": research_pack.get("claimLevel", "proxy"),
            "workflow": workflow.get("claimLevel", "demo"),
            "procurement": procurement.get("claimLevel", "demo"),
        },
    }
    metadata_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=True), encoding="utf-8")
    return metadata


def _prepare_pair(
    config: ReproductionConfig,
    output_dir: Path,
    *,
    prepared_pair_outputs: dict[str, str] | None,
    schema_path: str | Path | None,
) -> tuple[list[dict[str, Any]], dict[str, str], dict[str, Any]]:
    if prepared_pair_outputs is not None:
        pair_outputs = _validate_prepared_pair_outputs(prepared_pair_outputs)
        pair_result = _load_json(pair_outputs["pairResult"])
        validate_paired_experiment_result(pair_result, schema_path=schema_path)
        _verify_pair_output_payloads(pair_result, pair_outputs)
        commands = [
            {
                "role": "paired-experiment",
                "mode": "prepared-upstream",
                "modelId": pair_result["modelId"],
                "expectedPaths": pair_outputs,
            }
        ]
        return commands, pair_outputs, pair_result

    paired = config.paired_experiment
    pair_outputs = generate_and_write_abay_signal_pair(
        paired.source_analytics_path,
        paired.aggregate_demand_path,
        output_dir / paired.output_path,
        context_network_path=paired.context_network_path,
        seed=config.seed,
        baseline_delay_s=paired.baseline_delay_s,
        measure_delay_s=paired.measure_delay_s,
        affected_signals_per_trip=paired.affected_signals_per_trip,
        realization_factor=paired.realization_factor,
        claim_level=paired.claim_level,
        contract_schema_path=schema_path,
    )
    pair_result = _load_json(pair_outputs["pairResult"])
    commands = [
        {
            "role": "paired-experiment",
            "mode": "controlled-proxy-v1",
            "modelId": pair_result["modelId"],
            "parameters": {
                "baselineDelaySeconds": paired.baseline_delay_s,
                "measureDelaySeconds": paired.measure_delay_s,
                "affectedSignalsPerTrip": paired.affected_signals_per_trip,
                "realizationFactor": paired.realization_factor,
                "seed": config.seed,
            },
            "expectedPaths": pair_outputs,
        }
    ]
    return commands, pair_outputs, pair_result


def _generate_legacy_analytics(config: ReproductionConfig) -> list[dict[str, Any]]:
    """Retain the old generator seam for unrelated scripts; active Abay reproduction does not call it."""
    commands = []
    for analytics in config.analytics_runs:
        command = [
            sys.executable,
            "scripts/generate_analytics.py",
            "--pattern",
            analytics.pattern,
            "--seed",
            str(config.seed),
        ]
        if analytics.closed_streets:
            command.extend(["--closed_streets", analytics.closed_streets])
        import os

        env = {**os.environ, "TRAFFIC_SIM_REPRODUCIBLE_SYNTHETIC": "1"}
        result = subprocess.run(command, check=True, capture_output=True, text=True, env=env)
        expected_path = Path(analytics.path)
        generated_path = _analytics_output_path(analytics.pattern, analytics.closed_streets)
        if expected_path != generated_path:
            raise ValueError(f"Analytics config path {expected_path} does not match generated output {generated_path}")
        if not expected_path.exists():
            raise FileNotFoundError(f"Analytics command did not create expected path: {expected_path}")
        commands.append(
            {
                "role": analytics.role,
                "command": _display_command(command),
                "environment": {"TRAFFIC_SIM_REPRODUCIBLE_SYNTHETIC": "1"},
                "expectedPath": analytics.path,
                "stdout": result.stdout.strip(),
            }
        )
    return commands


def _write_reproduction_scenario_config(
    config: ReproductionConfig,
    output_dir: Path,
    provider_registry: dict[str, Any],
    *,
    pair_outputs: dict[str, str],
    release_run_id: str,
) -> Path:
    payload = json.loads(json.dumps(config.scenario_config))
    payload["seed"] = config.seed
    payload["releaseRunId"] = release_run_id
    payload["runPassportPath"] = str(output_dir / "run-passport.json")
    payload["outputDir"] = str(output_dir / "dossier")
    payload["dataSources"] = _reproduction_data_sources(provider_registry)
    payload["pairedExperimentPath"] = pair_outputs["pairResult"]
    payload["baseline"]["analyticsPath"] = pair_outputs["baselineAnalytics"]
    payload["measure"]["analyticsPath"] = pair_outputs["measureAnalytics"]
    path = output_dir / "scenario_config.json"
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")
    return path


def _write_trajectory_csv(
    config: ReproductionConfig,
    output_dir: Path,
    *,
    pair_outputs: dict[str, str],
) -> Path:
    path = output_dir / config.trajectory_path
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as file:
        fieldnames = [
            "scenario_id",
            "role",
            "seed",
            "hour",
            "congestion_index",
            "avg_speed_kph",
            "predicted_next_hour",
            "source_analytics_path",
            "claim_level",
        ]
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        analytics_by_role = {
            "baseline": pair_outputs["baselineAnalytics"],
            "measure": pair_outputs["measureAnalytics"],
        }
        for analytics in config.analytics_runs:
            analytics_path = analytics_by_role[analytics.role]
            payload = _load_json(analytics_path)
            series = payload.get("time_series", [])
            for index, item in enumerate(series):
                next_item = series[(index + 1) % len(series)] if series else {}
                writer.writerow(
                    {
                        "scenario_id": config.id,
                        "role": analytics.role,
                        "seed": config.seed,
                        "hour": item.get("hour"),
                        "congestion_index": item.get("congestion_index"),
                        "avg_speed_kph": item.get("avg_speed_kph"),
                        "predicted_next_hour": next_item.get("congestion_index"),
                        "source_analytics_path": analytics_path,
                        "claim_level": "proxy",
                    }
                )
    return path


def _write_reproduction_kpi_matrix(dossier: dict[str, Any], output_dir: Path) -> Path:
    path = output_dir / "portfolio" / "kpi_matrix.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    kpis = {item["id"]: item for item in dossier.get("executiveKpis", {}).get("kpis", []) if isinstance(item, dict) and "id" in item}
    with path.open("w", encoding="utf-8", newline="") as file:
        fieldnames = [
            "rank",
            "portfolio_id",
            "scenario_id",
            "scenario_name",
            "scenario_type",
            "corridor_id",
            "claim_level",
            "decision_signal",
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
            "analytics_path",
            "run_passport_path",
        ]
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerow(
            {
                "rank": 1,
                "portfolio_id": f"{dossier.get('id')}-reproduction",
                "scenario_id": dossier.get("id"),
                "scenario_name": dossier.get("proposedMeasure", {}).get("label"),
                "scenario_type": dossier.get("proposedMeasure", {}).get("type"),
                "corridor_id": dossier.get("corridor", {}).get("id"),
                "claim_level": dossier.get("claimLevel", "proxy"),
                "decision_signal": dossier.get("recommendation", {}).get("decision"),
                "person_hours_saved": _kpi_value(kpis, "person_hours_saved"),
                "corridor_speed_delta": _kpi_value(kpis, "corridor_speed_delta"),
                "queue_load_proxy": _kpi_value(kpis, "queue_load_proxy"),
                "bus_reliability_proxy": _kpi_value(kpis, "bus_reliability_proxy"),
                "co2_proxy": _kpi_value(kpis, "co2_proxy"),
                "nox_proxy": _kpi_value(kpis, "nox_proxy"),
                "capex_placeholder": _kpi_value(kpis, "capex_placeholder"),
                "opex_placeholder": _kpi_value(kpis, "opex_placeholder"),
                "annual_time_savings_proxy": _kpi_value(kpis, "annual_time_savings_proxy"),
                "roi_proxy": _kpi_value(kpis, "roi_proxy"),
                "payback_proxy": _kpi_value(kpis, "payback_proxy"),
                "analytics_path": dossier.get("proposedMeasure", {}).get("analyticsPath"),
                "run_passport_path": output_dir / "run-passport.json",
            }
        )
    return path


def _collect_generated_paths(
    *,
    scenario_config_path: Path,
    config: ReproductionConfig,
    provider_registry: dict[str, Any],
    dossier: dict[str, Any],
    trajectory_path: Path,
    kpi_matrix_path: Path,
    workflow: dict[str, Any],
    procurement: dict[str, Any],
    research_pack: dict[str, Any],
    pair_outputs: dict[str, str],
    dossier_paths: dict[str, str],
    workflow_paths: dict[str, str],
) -> list[tuple[str, str, str]]:
    paths: list[tuple[str, str, str]] = [
        ("scenario-config", str(scenario_config_path), "demo"),
        ("trajectory-csv", str(trajectory_path), "proxy"),
        ("portfolio-kpi-matrix", str(kpi_matrix_path), "proxy"),
        ("run-passport", str(Path(dossier["outputs"]["json"]).parents[1] / "run-passport.json"), "proxy"),
    ]
    paths.extend(
        [
            ("paired-experiment", pair_outputs["pairResult"], "proxy"),
            ("analytics", pair_outputs["baselineAnalytics"], "proxy"),
            ("analytics", pair_outputs["measureAnalytics"], "proxy"),
        ]
    )
    provider_outputs = provider_registry.get("outputs", {})
    if provider_outputs.get("registryJson"):
        paths.append(("provider-registry", provider_outputs["registryJson"], "demo"))
    if provider_outputs.get("roadsStatusJson"):
        paths.append(("roads-provider-status", provider_outputs["roadsStatusJson"], _provider_claim(provider_registry, "roads-geojson")))
    paths.extend(("dossier", path, dossier.get("claimLevel", "proxy")) for path in dossier_paths.values())
    paths.extend(("workflow", path, workflow.get("claimLevel", "demo")) for path in workflow_paths.values())
    paths.extend(("procurement", path, procurement.get("claimLevel", "demo")) for path in procurement.get("outputs", {}).values())
    paths.extend(("research-metrics", path, research_pack.get("claimLevel", "proxy")) for path in research_pack.get("outputs", {}).values())
    return paths


def _artifact_manifest(paths: list[tuple[str, str, str]], *, run_id: str) -> dict[str, Any]:
    artifacts = []
    for kind, path_text, claim_level in paths:
        path = Path(path_text)
        if not path.exists():
            raise FileNotFoundError(f"Generated artifact is missing: {path}")
        artifacts.append(
            {
                "kind": kind,
                "path": str(path),
                "claimLevel": claim_level,
                "bytes": path.stat().st_size,
                "sha256": _sha256(path),
            }
        )
    return {
        "id": "abay-first-epic-artifact-manifest",
        "kind": "reproduction-artifact-manifest",
        "claimLevel": "demo",
        "runId": run_id,
        "createdAt": _now(),
        "artifacts": artifacts,
    }


def _display_command(command: list[str]) -> list[str]:
    return ["python3" if item == sys.executable else item for item in command]


def _reproduction_data_sources(provider_registry: dict[str, Any]) -> list[dict[str, Any]]:
    sources = default_data_sources()
    for source in sources:
        if source.get("id") == "provider-registry":
            source["path"] = provider_registry["outputs"]["registryJson"]
        if source.get("id") == "roads-provider-status":
            source["path"] = provider_registry["outputs"]["roadsStatusJson"]
    return sources


def _kpi_value(kpis: dict[str, dict[str, Any]], kpi_id: str) -> Any:
    return kpis.get(kpi_id, {}).get("measure")


def _provider_claim(provider_registry: dict[str, Any], provider_id: str) -> str:
    for provider in provider_registry.get("providers", []):
        if provider.get("id") == provider_id:
            return str(provider.get("claim_label", "demo"))
    return "demo"


def _analytics_output_path(pattern: str, closed_streets: str) -> Path:
    name = f"analytics_{pattern}"
    if closed_streets:
        name += "_" + "".join(char if char.isalnum() else "_" for char in closed_streets)
    return Path("data") / f"{name}.json"


def _validate_prepared_pair_outputs(outputs: dict[str, str]) -> dict[str, str]:
    expected = {"pairResult", "baselineAnalytics", "measureAnalytics"}
    if set(outputs) != expected:
        raise ValueError(f"prepared_pair_outputs must contain exactly {sorted(expected)}")
    normalized = {key: str(Path(value)) for key, value in outputs.items()}
    for key, value in normalized.items():
        if not Path(value).is_file():
            raise FileNotFoundError(f"Prepared pair output {key} is missing: {value}")
    return normalized


def _verify_pair_output_payloads(pair: dict[str, Any], outputs: dict[str, str]) -> None:
    baseline = _load_json(outputs["baselineAnalytics"])
    measure = _load_json(outputs["measureAnalytics"])
    if canonical_json(baseline) != canonical_json(pair["baseline"]["analytics"]):
        raise ValueError("Prepared baseline analytics do not match the paired result")
    if canonical_json(measure) != canonical_json(pair["measure"]["analytics"]):
        raise ValueError("Prepared measure analytics do not match the paired result")


def _load_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _input_fingerprints(paths: list[Path]) -> list[dict[str, Any]]:
    fingerprints = []
    for path in paths:
        fingerprints.append(
            {
                "path": str(path),
                "available": path.exists(),
                "sha256": _sha256(path) if path.exists() and path.is_file() else None,
                "bytes": path.stat().st_size if path.exists() and path.is_file() else None,
            }
        )
    return fingerprints


def _source_control_status() -> dict[str, Any]:
    status = _git(["status", "--short"])
    lines = status.splitlines() if status else []
    return {
        "gitHash": _git(["rev-parse", "--short", "HEAD"]) or None,
        "dirty": bool(lines),
        "dirtyEntryCount": len(lines),
        "note": "Dirty state is expected during active agent work; use a clean checkout for procurement-ready reproduction evidence.",
    }


def _git(args: list[str]) -> str:
    try:
        result = subprocess.run(["git", *args], check=True, capture_output=True, text=True)
    except (subprocess.CalledProcessError, OSError):
        return ""
    return result.stdout.strip()


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
