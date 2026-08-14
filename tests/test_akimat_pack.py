from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from traffic_sim.akimat_pack import generate_akimat_application_pack


class AkimatApplicationPackTests(unittest.TestCase):
    def test_pack_generates_required_application_artifacts_without_claim_upgrade(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            pack = generate_akimat_application_pack(tmp_dir)
            files = pack["files"]

            required_roles = {
                "application_summary_md",
                "application_summary_html",
                "evidence_manifest_json",
                "missing_evidence_json",
                "pilot_acceptance_criteria_json",
                "procurement_pack_index_json",
                "data_request_memo_md",
                "data_readiness_json",
                "pilot_monitoring_plan_json",
                "pilot_monitoring_plan_md",
                "executive_brief_md",
                "demo_script_md",
                "slide_outline_md",
                "risk_register_json",
                "application_package_index_json",
                "scenario_alternative_comparison_json",
            }
            self.assertTrue(required_roles <= set(files))
            self.assertEqual(pack["claimLevel"], "demo")

            for path in files.values():
                self.assertTrue(Path(path).exists(), path)

            evidence_manifest = json.loads(Path(files["evidence_manifest_json"]).read_text(encoding="utf-8"))
            self.assertEqual(evidence_manifest["claimLevel"], "demo")
            self.assertEqual(evidence_manifest["claimBoundary"]["dossierClaimLevel"], "proxy")
            self.assertTrue(
                all(item["sha256"] for item in evidence_manifest["sourceArtifacts"] if item["available"])
            )

            missing = json.loads(Path(files["missing_evidence_json"]).read_text(encoding="utf-8"))
            missing_ids = {item["id"] for item in missing["items"]}
            self.assertTrue(
                {
                    "observed-corridor-speed-counts",
                    "bus-travel-time-reliability",
                    "current-signal-timing-plan",
                    "incident-roadwork-history",
                    "capex-opex-estimates",
                    "nominated-reviewer-data-steward",
                    "legal-feed-permissions",
                }
                <= missing_ids
            )

            pilot = json.loads(Path(files["pilot_acceptance_criteria_json"]).read_text(encoding="utf-8"))
            kpis = {item["kpi_id"] for item in pilot["criteria"]}
            self.assertTrue(
                {
                    "person_hours_saved",
                    "corridor_speed_delta",
                    "bus_reliability_proxy",
                    "capex_placeholder",
                }
                <= kpis
            )

            comparison = json.loads(Path(files["scenario_alternative_comparison_json"]).read_text(encoding="utf-8"))
            scenario_ids = {item["scenarioId"] for item in comparison["alternatives"]}
            self.assertTrue({"no-build-baseline", "abay-signal-retiming"} <= scenario_ids)

            buyer_text = "\n".join(
                Path(files[role]).read_text(encoding="utf-8")
                for role in [
                    "application_summary_md",
                    "executive_brief_md",
                    "data_request_memo_md",
                    "pilot_monitoring_plan_md",
                    "claim_boundary_md",
                ]
            )
            forbidden = [
                "AI proves",
                "guaranteed improvement",
                "live city data",
                "autonomous traffic control",
                "legal approval workflow exists",
            ]
            for phrase in forbidden:
                self.assertNotIn(phrase, buyer_text)


if __name__ == "__main__":
    unittest.main()
