from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from traffic_sim.research_metrics import generate_research_metrics_pack


class ResearchMetricsTests(unittest.TestCase):
    def test_research_pack_has_formulas_and_visual(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            baseline_path = root / "baseline.analytics.json"
            measure_path = root / "measure.analytics.json"
            dossier_path = root / "dossier.json"
            matrix_path = root / "kpi_matrix.csv"
            output_dir = root / "research"
            hours = [f"{hour:02d}:00" for hour in range(24)]
            baseline_path.write_text(
                json.dumps(
                    {
                        "time_series": [
                            {"hour": hour, "congestion_index": 50 + index}
                            for index, hour in enumerate(hours)
                        ]
                    }
                ),
                encoding="utf-8",
            )
            measure_path.write_text(
                json.dumps(
                    {
                        "time_series": [
                            {"hour": hour, "congestion_index": 47 + index}
                            for index, hour in enumerate(hours)
                        ]
                    }
                ),
                encoding="utf-8",
            )
            dossier = {
                "id": "abay-signal-retiming",
                "trustMetadata": {"runId": "research-test-run"},
                "baseline": {"analyticsPath": str(baseline_path)},
                "proposedMeasure": {"analyticsPath": str(measure_path)},
                "executiveKpis": {
                    "kpis": [
                        {"id": "bus_reliability_proxy", "measure": 82.0},
                        {"id": "queue_load_proxy", "delta": -0.2},
                        {"id": "co2_proxy", "delta": -4.0},
                        {"id": "nox_proxy", "delta": -0.1},
                        {"id": "person_hours_saved", "measure": 12.0},
                    ]
                },
            }
            dossier_path.write_text(json.dumps(dossier), encoding="utf-8")
            with matrix_path.open("w", encoding="utf-8", newline="") as file:
                writer = csv.DictWriter(file, fieldnames=["scenario_id", "person_hours_saved"])
                writer.writeheader()
                writer.writerow({"scenario_id": "abay-signal-retiming", "person_hours_saved": "12"})
            pack = generate_research_metrics_pack(
                dossier_path=dossier_path,
                portfolio_matrix_path=matrix_path,
                out_dir=output_dir,
                dossier=dossier,
            )
            metric_ids = {metric["id"] for metric in pack["metrics"]}
            self.assertTrue(
                {
                    "reliability_index",
                    "emissions_proxy",
                    "person_hours_sensitivity_interval",
                    "scenario_kpi_matrix",
                    "network_hour_heatmap",
                }
                <= metric_ids
            )
            self.assertEqual(pack["claimLevel"], "proxy")
            self.assertTrue(all(metric["formula"] for metric in pack["metrics"]))
            self.assertTrue(all(metric["officialFacingReason"] for metric in pack["metrics"]))
            self.assertEqual(len(pack["visualization"]["data"]), 24)
            matrix_metric = next(metric for metric in pack["metrics"] if metric["id"] == "scenario_kpi_matrix")
            self.assertEqual(matrix_metric["value"]["bestByPersonHoursSaved"], "abay-signal-retiming")
            self.assertTrue((output_dir / "research_metrics.json").exists())
            self.assertTrue((output_dir / "dossier_appendix.md").exists())
            self.assertTrue((output_dir / "research_visual.html").exists())
            payload = json.loads((output_dir / "research_metrics.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["id"], pack["id"])


if __name__ == "__main__":
    unittest.main()
