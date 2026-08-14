from __future__ import annotations

import csv
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from traffic_sim.config import load_reproduction_config
from traffic_sim.paired_experiment import generate_and_write_abay_signal_pair
from traffic_sim.reproducibility import generate_reproduction_run


class ReproducibilityTests(unittest.TestCase):
    def test_config_loads_fixed_seed_and_required_runs(self) -> None:
        config = load_reproduction_config("simulation.config.json")
        self.assertEqual(config.seed, 7)
        self.assertEqual(config.claim_level, "demo")
        self.assertEqual(config.scenario_config["id"], "abay-signal-retiming")
        self.assertEqual({item.role for item in config.analytics_runs}, {"baseline", "measure"})
        self.assertEqual(config.paired_experiment.baseline_delay_s, 36)
        self.assertEqual(config.paired_experiment.measure_delay_s, 32)
        self.assertEqual(config.paired_experiment.claim_level, "proxy")
        self.assertNotIn("closed_streets", json.dumps(config.scenario_config))

    def test_reproduction_config_is_closed_and_self_consistent(self) -> None:
        base = json.loads(Path("simulation.config.json").read_text(encoding="utf-8"))
        mutations = {
            "unknown top-level": lambda payload: payload.__setitem__("scenarioConfig", "fallback.json"),
            "unknown pair field": lambda payload: payload["pairedExperiment"].__setitem__(
                "unregistered", True
            ),
            "unknown embedded scenario field": lambda payload: payload["scenario"]["measure"].__setitem__(
                "unregistered", True
            ),
            "delay drift": lambda payload: payload["pairedExperiment"].__setitem__(
                "measureDelaySeconds", 31
            ),
        }
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "simulation.config.json"
            for label, mutate in mutations.items():
                with self.subTest(label=label):
                    payload = json.loads(json.dumps(base))
                    mutate(payload)
                    path.write_text(json.dumps(payload), encoding="utf-8")
                    with self.assertRaisesRegex(ValueError, "invalid fields|config drift"):
                        load_reproduction_config(path)

    def test_reproduction_run_writes_metadata_manifest_and_trajectory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            metadata = generate_reproduction_run(
                "simulation.config.json",
                out_dir=tmp_dir,
                release_run_id="release-run-test-001",
            )
            metadata_path = Path(metadata["outputs"]["metadata"])
            manifest_path = Path(metadata["outputs"]["artifactManifest"])
            trajectory_path = Path(metadata["outputs"]["trajectoryCsv"])
            kpi_matrix_path = Path(metadata["outputs"]["kpiMatrix"])
            dossier_path = Path(metadata["outputs"]["dossier"]["json"])
            run_passport_path = Path(metadata["outputs"]["runPassport"])

            self.assertEqual(metadata["seed"], 7)
            self.assertEqual(metadata["releaseRunId"], "release-run-test-001")
            self.assertEqual(metadata["pairedExperiment"]["modelId"], "abay-signal-delay-proxy-v1")
            self.assertEqual(metadata["pairedExperiment"]["demandControl"]["modeledVehicleCount"], 500)
            self.assertIn("sourceControl", metadata)
            self.assertTrue(metadata["inputFingerprints"])
            self.assertEqual(metadata["commands"][0]["mode"], "controlled-proxy-v1")
            self.assertTrue(metadata_path.exists())
            self.assertTrue(manifest_path.exists())
            self.assertTrue(trajectory_path.exists())
            self.assertTrue(kpi_matrix_path.exists())
            self.assertTrue(dossier_path.exists())
            self.assertTrue(run_passport_path.exists())

            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["runId"], "release-run-test-001")
            self.assertEqual(len(manifest["artifacts"]), 22)
            self.assertTrue(all(item["sha256"] for item in manifest["artifacts"]))
            self.assertTrue(any(item["kind"] == "paired-experiment" for item in manifest["artifacts"]))
            self.assertTrue(any(item["kind"] == "portfolio-kpi-matrix" for item in manifest["artifacts"]))
            self.assertTrue(str(kpi_matrix_path).endswith("portfolio/kpi_matrix.csv"))
            road_status = next(item for item in manifest["artifacts"] if item["path"].endswith("roads_geojson_provider_status.json"))
            self.assertEqual(road_status["claimLevel"], "real-data")

            run_passport = json.loads(run_passport_path.read_text(encoding="utf-8"))
            self.assertEqual(run_passport["runId"], "release-run-test-001")
            self.assertEqual(run_passport["claimLabels"]["calibration"], "proxy")
            self.assertEqual(run_passport["calibrationValidation"]["claimLabel"], "proxy")
            calibration_source = next(item for item in run_passport["dataSources"] if item["id"] == "calibration-layer")
            self.assertEqual(calibration_source["claim_label"], "proxy")
            provider_source = next(item for item in run_passport["dataSources"] if item["id"] == "provider-registry")
            self.assertEqual(provider_source["path"], metadata["outputs"]["providerRegistry"]["registryJson"])
            road_provider_source = next(item for item in run_passport["dataSources"] if item["id"] == "roads-provider-status")
            self.assertEqual(road_provider_source["path"], metadata["outputs"]["providerRegistry"]["roadsStatusJson"])

            with trajectory_path.open(encoding="utf-8", newline="") as file:
                rows = list(csv.DictReader(file))
            self.assertEqual(len(rows), 48)
            self.assertEqual({row["role"] for row in rows}, {"baseline", "measure"})
            self.assertTrue(all(row["seed"] == "7" for row in rows))
            baseline_rows = [row for row in rows if row["role"] == "baseline"]
            measure_rows = [row for row in rows if row["role"] == "measure"]
            self.assertEqual([row["hour"] for row in baseline_rows], [row["hour"] for row in measure_rows])

    def test_output_relative_paths_reject_traversal(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            bad_config = Path(tmp_dir) / "bad.config.json"
            payload = json.loads(Path("simulation.config.json").read_text(encoding="utf-8"))
            payload["trajectoryExport"]["path"] = "../escape.csv"
            bad_config.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "trajectoryExport.path"):
                load_reproduction_config(bad_config)

            payload = json.loads(Path("simulation.config.json").read_text(encoding="utf-8"))
            payload["outputRoot"] = "/tmp/outside"
            bad_config.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "outputRoot"):
                load_reproduction_config(bad_config)

            payload = json.loads(Path("simulation.config.json").read_text(encoding="utf-8"))
            payload["pairedExperiment"]["sourceAnalyticsPath"] = "../source.json"
            bad_config.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "pairedExperiment.sourceAnalyticsPath"):
                load_reproduction_config(bad_config)

    def test_prepared_pair_seam_does_not_rerun_analytics_generator(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            pair_outputs = generate_and_write_abay_signal_pair(
                "data/fixtures/abay/source-analytics.proxy-v1.json",
                "data/fixtures/abay/aggregate-demand.proxy-v1.json",
                Path(tmp_dir) / "prepared-pair",
                context_network_path="data/almaty_roads.geojson",
            )
            metadata = generate_reproduction_run(
                "simulation.config.json",
                out_dir=Path(tmp_dir) / "repro",
                prepared_pair_outputs=pair_outputs,
            )
            self.assertEqual(metadata["releaseRunId"], "abay-first-epic-reproduction")
            default_passport = json.loads(
                Path(metadata["outputs"]["runPassport"]).read_text(encoding="utf-8")
            )
            self.assertEqual(default_passport["runId"], "abay-first-epic-reproduction")
            self.assertEqual(metadata["commands"], [
                {
                    "role": "paired-experiment",
                    "mode": "prepared-upstream",
                    "modelId": "abay-signal-delay-proxy-v1",
                    "expectedPaths": pair_outputs,
                }
            ])
            self.assertEqual(metadata["pairedExperiment"]["semanticFingerprint"], json.loads(Path(pair_outputs["pairResult"]).read_text(encoding="utf-8"))["semanticFingerprint"])

    def test_legacy_analytics_cli_remains_callable_outside_active_pair(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            result = subprocess.run(
                [
                    sys.executable,
                    str(Path("scripts/generate_analytics.py").resolve()),
                    "--pattern",
                    "normal",
                    "--seed",
                    "7",
                ],
                cwd=tmp_dir,
                env={**os.environ, "TRAFFIC_SIM_REPRODUCIBLE_SYNTHETIC": "1"},
                check=True,
                capture_output=True,
                text=True,
            )
            output = Path(tmp_dir) / "data" / "analytics_normal.json"
            self.assertTrue(output.is_file(), result.stdout)
            payload = json.loads(output.read_text(encoding="utf-8"))
            self.assertIn("executive_kpis", payload)


if __name__ == "__main__":
    unittest.main()
