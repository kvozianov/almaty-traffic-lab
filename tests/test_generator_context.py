from __future__ import annotations

from contextlib import contextmanager
import csv
import json
import os
from pathlib import Path
import tempfile
import unittest
from typing import Any, Iterator

from traffic_sim.akimat_pack import (
    GENERATED_FILE_ROLES,
    OPTIONAL_INPUT_PATHS,
    REQUIRED_INPUT_PATHS,
    generate_akimat_application_pack,
)
from traffic_sim.data_sources import DEFAULT_SOURCE_PATHS, write_provider_registry
from traffic_sim.procurement import DEFAULT_EVIDENCE_REFS, generate_procurement_packet
from traffic_sim.research_metrics import generate_research_metrics_pack
from traffic_sim.run_metadata import build_run_passport
from traffic_sim.workflow import generate_decision_workflow


REPO_ROOT = Path(__file__).resolve().parents[1]


@contextmanager
def _working_directory(path: Path) -> Iterator[None]:
    previous = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True), encoding="utf-8")


def _copy_input(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(source.read_bytes())


class ExplicitGeneratorContextTests(unittest.TestCase):
    def test_akimat_pack_uses_only_injected_inputs_and_logical_refs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            staging = root / ".staging-current"
            poison = root / "poison-root"
            poison.mkdir()

            inputs: dict[str, Path] = {}
            for role, relative_path in (dict(REQUIRED_INPUT_PATHS) | dict(OPTIONAL_INPUT_PATHS)).items():
                source = REPO_ROOT / relative_path
                target = staging / "upstream" / role / source.name
                _copy_input(source, target)
                inputs[role] = target.resolve()

            passport = json.loads(inputs["runPassport"].read_text(encoding="utf-8"))
            passport["runId"] = "current-run"
            _write_json(inputs["runPassport"], passport)

            for relative_path in REQUIRED_INPUT_PATHS.values():
                _write_json(
                    poison / relative_path,
                    {"id": "stale-root", "runId": "stale-root", "marker": "STALE_ROOT"},
                )
            for relative_path in OPTIONAL_INPUT_PATHS.values():
                target = poison / relative_path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text("STALE_ROOT", encoding="utf-8")

            evidence_refs = {
                role: f"artifacts/upstream/{role}{path.suffix}"
                for role, path in inputs.items()
            }
            output_refs = {
                role: f"artifacts/akimat/{role}"
                for role in GENERATED_FILE_ROLES
            }
            output_dir = staging / "artifacts" / "akimat"
            with _working_directory(poison):
                pack = generate_akimat_application_pack(
                    output_dir,
                    inputs=inputs,
                    evidence_refs=evidence_refs,
                    output_refs=output_refs,
                )

            summary = Path(pack["files"]["application_summary_md"]).read_text(encoding="utf-8")
            self.assertIn("current-run", summary)
            self.assertNotIn("STALE_ROOT", summary)

            manifest = json.loads(
                Path(pack["files"]["evidence_manifest_json"]).read_text(encoding="utf-8")
            )
            source_paths = [item["path"] for item in manifest["sourceArtifacts"]]
            generated_paths = [item["path"] for item in manifest["generatedArtifacts"]]
            self.assertEqual(set(source_paths), set(evidence_refs.values()))
            self.assertTrue(set(generated_paths) <= set(output_refs.values()))
            self.assertTrue(all(not Path(path).is_absolute() for path in source_paths + generated_paths))

            forbidden = (str(root), ".staging", "STALE_ROOT")
            for role, path in pack["files"].items():
                if Path(path).suffix != ".json":
                    continue
                text = Path(path).read_text(encoding="utf-8")
                for marker in forbidden:
                    self.assertNotIn(marker, text, f"{marker!r} leaked into {role}")

    def test_workflow_and_research_ignore_poisoned_embedded_root_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            staging = root / ".staging-current"
            poison = root / "poison-root"
            poison.mkdir()

            dossier = json.loads(
                (REPO_ROOT / "reports/dossiers/abay-signal-retiming/dossier.json").read_text(
                    encoding="utf-8"
                )
            )
            dossier["id"] = "current-scenario"
            dossier["outputs"] = {
                "json": "reports/poison/dossier.json",
                "markdown": "reports/poison/dossier.md",
                "html": "reports/poison/dossier.html",
                "kpisCsv": "reports/poison/kpis.csv",
            }
            dossier["baseline"]["analyticsPath"] = "reports/poison/baseline.json"
            dossier["proposedMeasure"]["analyticsPath"] = "reports/poison/measure.json"

            dossier_path = staging / "dossier" / "dossier.json"
            dossier_markdown = staging / "dossier" / "dossier.md"
            passport_path = staging / "passport" / "run-passport.json"
            _write_json(dossier_path, dossier)
            dossier_markdown.parent.mkdir(parents=True, exist_ok=True)
            dossier_markdown.write_text("CURRENT DOSSIER", encoding="utf-8")
            _write_json(passport_path, {"runId": "current-run"})

            _write_json(poison / "reports/poison/dossier.json", {"id": "stale-root"})
            (poison / "reports/poison").mkdir(parents=True, exist_ok=True)
            (poison / "reports/poison/dossier.md").write_text("STALE_ROOT", encoding="utf-8")
            _write_json(
                poison / "reports/poison/baseline.json",
                {"time_series": [{"hour": "08:00", "congestion_index": 99}]},
            )
            _write_json(
                poison / "reports/poison/measure.json",
                {"time_series": [{"hour": "08:00", "congestion_index": 98}]},
            )

            workflow_paths = {
                "dossierJson": dossier_path.resolve(),
                "dossierMarkdown": dossier_markdown.resolve(),
                "runPassport": passport_path.resolve(),
            }
            workflow_refs = {
                "dossierJson": "artifacts/dossier/dossier.json",
                "dossierMarkdown": "artifacts/dossier/dossier.md",
                "runPassport": "artifacts/run-passport.json",
                "workflowJson": "artifacts/workflow/workflow.json",
                "engineerTasksCsv": "artifacts/workflow/tasks.csv",
                "monitoringJson": "artifacts/workflow/monitoring.json",
                "postAuditJson": "artifacts/workflow/post-audit.json",
                "claimLedger": "sources/claim-ledger.md",
            }
            with _working_directory(poison):
                workflow = generate_decision_workflow(
                    out_dir=staging / "workflow",
                    artifact_paths=workflow_paths,
                    artifact_refs=workflow_refs,
                )

            self.assertEqual(workflow["scenarioId"], "current-scenario")
            self.assertEqual(workflow["dossier"]["path"], workflow_refs["dossierJson"])
            self.assertEqual(workflow["outputs"]["workflowJson"], workflow_refs["workflowJson"])
            self.assertTrue(
                all(item["path"] in workflow_refs.values() for item in workflow["artifactLocks"])
            )
            workflow_text = (staging / "workflow/current-scenario-decision-workflow.json").read_text(
                encoding="utf-8"
            )
            self.assertNotIn(str(root), workflow_text)
            self.assertNotIn(".staging", workflow_text)
            self.assertNotIn("reports/poison", workflow_text)

            baseline_path = staging / "analytics" / "baseline.json"
            measure_path = staging / "analytics" / "measure.json"
            _write_json(
                baseline_path,
                {"time_series": [{"hour": "08:00", "congestion_index": 10}]},
            )
            _write_json(
                measure_path,
                {"time_series": [{"hour": "08:00", "congestion_index": 5}]},
            )
            matrix_path = staging / "portfolio" / "kpi_matrix.csv"
            matrix_path.parent.mkdir(parents=True, exist_ok=True)
            with matrix_path.open("w", encoding="utf-8", newline="") as file:
                writer = csv.DictWriter(file, fieldnames=["scenario_id", "person_hours_saved"])
                writer.writeheader()
                writer.writerow({"scenario_id": "current-scenario", "person_hours_saved": "1"})

            research_inputs = {
                "dossierJson": dossier_path.resolve(),
                "portfolioMatrix": matrix_path.resolve(),
                "baselineAnalytics": baseline_path.resolve(),
                "measureAnalytics": measure_path.resolve(),
            }
            research_refs = {
                "dossierJson": "artifacts/dossier/dossier.json",
                "portfolioMatrix": "artifacts/portfolio/kpi_matrix.csv",
                "baselineAnalytics": "artifacts/analytics/baseline.json",
                "measureAnalytics": "artifacts/analytics/measure.json",
                "researchJson": "artifacts/research/research_metrics.json",
                "researchAppendix": "artifacts/research/dossier_appendix.md",
                "researchVisual": "artifacts/research/research_visual.html",
            }
            with _working_directory(poison):
                research = generate_research_metrics_pack(
                    out_dir=staging / "research",
                    input_paths=research_inputs,
                    artifact_refs=research_refs,
                )
            self.assertEqual(
                research["visualization"]["data"],
                [
                    {
                        "hour": "08:00",
                        "baselineCongestion": 10.0,
                        "measureCongestion": 5.0,
                        "delta": -5.0,
                    }
                ],
            )
            matrix_metric = next(
                item for item in research["metrics"] if item["id"] == "scenario_kpi_matrix"
            )
            self.assertEqual(matrix_metric["value"]["matrixPath"], research_refs["portfolioMatrix"])
            research_text = (staging / "research/research_metrics.json").read_text(encoding="utf-8")
            self.assertNotIn(str(root), research_text)
            self.assertNotIn(".staging", research_text)
            self.assertNotIn("reports/poison", research_text)

    def test_source_passport_and_procurement_contexts_are_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            staging = root / ".staging-current"
            poison = root / "poison-root"
            poison.mkdir()

            roads_path = staging / "sources/roads.geojson"
            traffic_path = staging / "sources/traffic.csv"
            scenarios_path = staging / "sources/scenarios.json"
            _write_json(
                roads_path,
                {"type": "FeatureCollection", "features": [{"id": 1}, {"id": 2}]},
            )
            traffic_path.parent.mkdir(parents=True, exist_ok=True)
            traffic_path.write_text("hour,value\n08:00,1\n", encoding="utf-8")
            _write_json(scenarios_path, {"scenarios": []})
            source_paths = {
                "roadsGeojson": roads_path.resolve(),
                "trafficProfileCsv": traffic_path.resolve(),
                "scenarioLibrary": scenarios_path.resolve(),
            }
            source_refs = {
                "roadsGeojson": "sources/roads.geojson",
                "trafficProfileCsv": "sources/traffic.csv",
                "scenarioLibrary": "sources/scenarios.json",
            }
            provider_output_refs = {
                "registryJson": "artifacts/providers/provider_registry.json",
                "roadsStatusJson": "artifacts/providers/roads_status.json",
            }
            with _working_directory(poison):
                registry = write_provider_registry(
                    staging / "providers",
                    source_paths=source_paths,
                    source_refs=source_refs,
                    artifact_refs=provider_output_refs,
                )
            roads = next(item for item in registry["providers"] if item["id"] == "roads-geojson")
            self.assertEqual(roads["feature_count"], 2)
            self.assertEqual(roads["path"], source_refs["roadsGeojson"])
            self.assertEqual(registry["outputs"], provider_output_refs)

            calibration_path = staging / "sources/calibration.json"
            _write_json(calibration_path, {"segments": [{"id": 1}]})
            passport_sources = [
                {
                    "id": "roads-geojson",
                    "label": "Roads",
                    "path": "data/poison-roads.geojson",
                    "claim_label": "real-data",
                    "source_type": "snapshot",
                },
                {
                    "id": "calibration-layer",
                    "label": "Calibration",
                    "path": "data/poison-calibration.json",
                    "claim_label": "proxy",
                    "source_type": "assumptions",
                },
            ]
            passport = build_run_passport(
                run_id="current-run",
                scenario_params={"scenarioId": "current-scenario"},
                seed=7,
                data_sources=passport_sources,
                source_paths={
                    "roads-geojson": roads_path.resolve(),
                    "calibration-layer": calibration_path.resolve(),
                },
                source_refs={
                    "roads-geojson": "sources/roads.geojson",
                    "calibration-layer": "sources/calibration.json",
                },
                project_context={
                    "name": "traffic-sim-almaty",
                    "version": "portfolio-test",
                    "gitHash": "deadbeef",
                },
                calibration_context={
                    "claimLabel": "proxy",
                    "path": "sources/calibration.json",
                    "available": True,
                    "segmentCount": 1,
                    "observedVsSimulated": [],
                    "notes": "Injected calibration context.",
                },
            )
            self.assertEqual(passport["model"]["version"], "portfolio-test")
            self.assertEqual(
                [item["path"] for item in passport["dataSources"]],
                ["sources/roads.geojson", "sources/calibration.json"],
            )
            self.assertEqual(passport["calibrationValidation"]["segmentCount"], 1)

            evidence_refs = {
                role: f"sources/procurement/{role}"
                for role in DEFAULT_EVIDENCE_REFS
            }
            procurement_output_refs = {
                "json": "artifacts/procurement/tender_checklist.json",
                "csv": "artifacts/procurement/tender_checklist.csv",
            }
            packet = generate_procurement_packet(
                staging / "procurement",
                evidence_refs=evidence_refs,
                artifact_refs=procurement_output_refs,
            )
            serialized_evidence = {
                ref
                for requirement in packet["requirements"]
                for ref in requirement["evidence"]
            }
            self.assertTrue(serialized_evidence <= set(evidence_refs.values()))
            self.assertEqual(packet["outputs"], procurement_output_refs)

    def test_explicit_maps_reject_missing_roles_and_unsafe_refs(self) -> None:
        incomplete_inputs = dict(REQUIRED_INPUT_PATHS)
        incomplete_inputs.pop("dossier")
        with self.assertRaisesRegex(ValueError, "missing=.*dossier"):
            generate_akimat_application_pack(inputs=incomplete_inputs)

        bad_source_refs = {role: f"sources/{role}" for role in DEFAULT_SOURCE_PATHS}
        bad_source_refs["roadsGeojson"] = "../escape.geojson"
        with self.assertRaisesRegex(ValueError, "Unsafe logical reference"):
            write_provider_registry(
                source_paths=DEFAULT_SOURCE_PATHS,
                source_refs=bad_source_refs,
            )

        with self.assertRaisesRegex(ValueError, "Unsafe logical reference"):
            generate_procurement_packet(
                evidence_refs=DEFAULT_EVIDENCE_REFS,
                artifact_refs={"json": ".staging/tender.json", "csv": "artifacts/tender.csv"},
            )

        with self.assertRaisesRegex(ValueError, "project_context is required"):
            build_run_passport(
                run_id="run",
                scenario_params={},
                seed=1,
                data_sources=[
                    {
                        "id": "calibration-layer",
                        "path": "calibration.json",
                        "claim_label": "proxy",
                    }
                ],
                source_paths={"calibration-layer": Path("calibration.json")},
                source_refs={"calibration-layer": "sources/calibration.json"},
            )


if __name__ == "__main__":
    unittest.main()
