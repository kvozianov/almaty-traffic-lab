from __future__ import annotations

import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

from traffic_sim.dossier import build_recommendation, generate_scenario_dossier
from traffic_sim.executive_kpis import (
    ExecutiveKpiAssumptions,
    build_executive_kpi_block,
    kpis_by_id,
)
from traffic_sim.paired_experiment import generate_and_write_abay_signal_pair


class ScenarioDossierTests(unittest.TestCase):
    def test_proxy_dossier_blocks_unqualified_fund_decision(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            config = json.loads(Path("data/scenarios/dossier_abay_signal.json").read_text(encoding="utf-8"))
            pair_outputs = generate_and_write_abay_signal_pair(
                "data/fixtures/abay/source-analytics.proxy-v1.json",
                "data/fixtures/abay/aggregate-demand.proxy-v1.json",
                Path(tmp_dir) / "pair",
                context_network_path="data/almaty_roads.geojson",
            )
            config["baseline"]["analyticsPath"] = pair_outputs["baselineAnalytics"]
            config["measure"]["analyticsPath"] = pair_outputs["measureAnalytics"]
            config["pairedExperimentPath"] = pair_outputs["pairResult"]
            config["baseline"]["analyticsLogicalPath"] = "artifacts/pair/baseline.analytics.json"
            config["measure"]["analyticsLogicalPath"] = "artifacts/pair/measure.analytics.json"
            config["pairedExperimentLogicalPath"] = "artifacts/pair/paired-experiment.json"
            config["outputLogicalDir"] = "artifacts/dossier"
            config["outputDir"] = f"{tmp_dir}/dossier"
            config["runPassportPath"] = f"{tmp_dir}/run-passport.json"
            config_path = Path(tmp_dir) / "dossier_abay_signal.json"
            config_path.write_text(json.dumps(config), encoding="utf-8")

            dossier = generate_scenario_dossier(
                config_path, release_run_id="portfolio-run-20260812"
            )
            allowed_decisions = dossier["recommendation"]["allowedDecisions"]

            self.assertEqual(dossier["claimLevel"], "proxy")
            self.assertEqual(
                allowed_decisions,
                [
                    "request_more_evidence",
                    "investigate_further",
                    "defer",
                    "fund_conditional_on_evidence",
                    "reject",
                ],
            )
            self.assertNotIn("fund", allowed_decisions)
            self.assertEqual(dossier["recommendation"]["decision"], "request_more_evidence")
            self.assertEqual(dossier["recommendation"]["mobilityState"], "M5_favorable_only")
            self.assertEqual(dossier["recommendation"]["economicsState"], "E1_incomplete")
            self.assertEqual(dossier["experiment"]["modelId"], "abay-signal-delay-proxy-v1")
            self.assertEqual(dossier["trustMetadata"]["runId"], "portfolio-run-20260812")
            passport = json.loads(Path(config["runPassportPath"]).read_text(encoding="utf-8"))
            self.assertEqual(passport["runId"], "portfolio-run-20260812")
            self.assertEqual(dossier["baseline"]["summary"]["total_active_vehicles"], 500)
            self.assertEqual(dossier["proposedMeasure"]["summary"]["total_active_vehicles"], 500)
            by_id = kpis_by_id(dossier["executiveKpis"])
            self.assertEqual(
                dossier["executiveKpis"]["assumptions"]["averageVehicleOccupancy"], 1.0
            )
            self.assertEqual(
                dossier["executiveKpis"]["assumptions"]["averageVehicleOccupancyClaimLevel"],
                "proxy",
            )
            self.assertIn(
                "average_vehicle_occupancy",
                by_id["person_hours"]["formula"],
            )
            self.assertEqual(by_id["capex_placeholder"]["measure"], 350000000.0)
            self.assertEqual(by_id["opex_placeholder"]["measure"], 25000000.0)
            compatibility = json.loads(
                Path("tests/fixtures/dossier-abay-signal-retiming.v1.json").read_text(encoding="utf-8")
            )
            self.assertTrue(set(compatibility["requiredTopLevelKeys"]).issubset(dossier))
            self.assertEqual(
                [
                    {
                        "id": item["id"],
                        "direction": item["direction"],
                        "claimLevel": item["claimLevel"],
                        "placeholder": item["placeholder"],
                    }
                    for item in dossier["executiveKpis"]["kpis"]
                ],
                compatibility["kpis"],
            )
            for key, value in compatibility["recommendation"].items():
                self.assertEqual(dossier["recommendation"][key], value)
            self.assertEqual(list(dossier["outputs"]), compatibility["artifactRoles"])
            self.assertEqual(dossier["outputs"]["json"], "artifacts/dossier/dossier.json")
            self.assertEqual(dossier["baseline"]["analyticsPath"], "artifacts/pair/baseline.analytics.json")
            self.assertNotIn(tmp_dir, json.dumps(dossier))

    def test_kpi_builder_rejects_incomparable_demand_and_uses_one_count(self) -> None:
        baseline = _analytics(36)
        measure = _analytics(32)
        measure["demandControl"] = deepcopy(measure["demandControl"])
        measure["demandControl"]["modeledVehicleCount"] = 501
        measure["summary"]["total_active_vehicles"] = 501
        with self.assertRaisesRegex(ValueError, "demandControl"):
            build_executive_kpi_block(baseline, measure)

    def test_recommendation_covers_all_claim_economics_matrix_cells(self) -> None:
        claims = ["demo", "proxy", "calibrated", "real-data", "procurement-ready"]
        expected = {
            "demo": {"E1_incomplete": "request_more_evidence", "E2_positive": "request_more_evidence", "E3_non_positive": "request_more_evidence"},
            "proxy": {"E1_incomplete": "request_more_evidence", "E2_positive": "request_more_evidence", "E3_non_positive": "request_more_evidence"},
            "calibrated": {"E1_incomplete": "request_more_evidence", "E2_positive": "defer", "E3_non_positive": "defer"},
            "real-data": {"E1_incomplete": "request_more_evidence", "E2_positive": "request_more_evidence", "E3_non_positive": "defer"},
            "procurement-ready": {"E1_incomplete": "request_more_evidence", "E2_positive": "fund_conditional_on_evidence", "E3_non_positive": "reject"},
        }
        for claim in claims:
            for economics in ("E1_incomplete", "E2_positive", "E3_non_positive"):
                with self.subTest(claim=claim, economics=economics):
                    block = _favorable_block(claim, economics)
                    recommendation = build_recommendation(block, claim_level=claim)
                    self.assertEqual(recommendation["mobilityState"], "M5_favorable_only")
                    self.assertEqual(recommendation["economicsState"], economics)
                    self.assertEqual(recommendation["decision"], expected[claim][economics])
                    self.assertNotEqual(recommendation["decision"], "fund")
                    if claim == "real-data" and economics == "E2_positive":
                        self.assertIn("provenance, not model calibration", recommendation["rationale"])

    def test_recommendation_ordered_mobility_states(self) -> None:
        block = _favorable_block("proxy", "E2_positive")
        by_id = kpis_by_id(block)
        by_id["person_hours"]["available"] = False
        result = build_recommendation(block, claim_level="proxy")
        self.assertEqual((result["ruleId"], result["decision"]), ("M1", "request_more_evidence"))

        block = _favorable_block("proxy", "E2_positive")
        by_id = kpis_by_id(block)
        by_id["corridor_speed_delta"]["measure"] = by_id["corridor_speed_delta"]["baseline"] - 1
        by_id["corridor_speed_delta"]["delta"] = -1
        result = build_recommendation(block, claim_level="proxy")
        self.assertEqual((result["ruleId"], result["decision"]), ("M2", "request_more_evidence"))

        block = _favorable_block("proxy", "E2_positive")
        for item in block["kpis"]:
            if item["id"] in {"person_hours", "corridor_speed_delta", "queue_load_proxy", "bus_reliability_proxy", "co2_proxy", "nox_proxy"}:
                item["measure"] = item["baseline"]
                item["delta"] = 0.0
        result = build_recommendation(block, claim_level="proxy")
        self.assertEqual((result["ruleId"], result["decision"]), ("M4", "request_more_evidence"))

        block = _favorable_block("proxy", "E2_positive")
        for item in block["kpis"]:
            if item["id"] in {"person_hours", "corridor_speed_delta", "queue_load_proxy", "bus_reliability_proxy", "co2_proxy", "nox_proxy"}:
                direction = item["direction"]
                item["measure"] = item["baseline"] + (1 if direction == "lower_is_better" else -1)
                item["delta"] = item["measure"] - item["baseline"]
        result = build_recommendation(block, claim_level="proxy")
        self.assertEqual((result["ruleId"], result["decision"]), ("M3", "reject"))

    def test_unknown_claim_level_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "claim level"):
            build_recommendation(_favorable_block("proxy", "E2_positive"), claim_level="invented")

    def test_recommendation_rejects_claim_upgrade_and_duplicate_kpi_rows(self) -> None:
        block = _favorable_block("proxy", "E2_positive")
        with self.assertRaisesRegex(ValueError, "block claimLevel"):
            build_recommendation(block, claim_level="procurement-ready")

        forged_row = deepcopy(block)
        forged_row["kpis"][0]["claimLevel"] = "procurement-ready"
        with self.assertRaisesRegex(ValueError, "KPI row .* claimLevel"):
            build_recommendation(forged_row, claim_level="proxy")

        forged_confidence = deepcopy(block)
        forged_confidence["confidence"]["claimLevel"] = "real-data"
        with self.assertRaisesRegex(ValueError, "confidence claimLevel"):
            build_recommendation(forged_confidence, claim_level="proxy")

        forged_occupancy_claim = deepcopy(block)
        forged_occupancy_claim["assumptions"]["averageVehicleOccupancyClaimLevel"] = "real-data"
        with self.assertRaisesRegex(ValueError, "averageVehicleOccupancy.*proxy claim"):
            build_recommendation(forged_occupancy_claim, claim_level="proxy")

        duplicate = deepcopy(block)
        duplicate["kpis"].append(deepcopy(duplicate["kpis"][0]))
        with self.assertRaisesRegex(ValueError, "duplicate id"):
            build_recommendation(duplicate, claim_level="proxy")

    def test_average_vehicle_occupancy_is_explicit_and_scales_people_not_emissions(self) -> None:
        baseline = _analytics(36)
        measure = _analytics(32)
        default = build_executive_kpi_block(baseline, measure)
        double = build_executive_kpi_block(
            baseline,
            measure,
            assumptions=ExecutiveKpiAssumptions(average_vehicle_occupancy=2.0),
        )
        default_by_id = kpis_by_id(default)
        double_by_id = kpis_by_id(double)
        for kpi_id in ("person_hours", "person_hours_saved", "annual_time_savings_proxy"):
            self.assertLessEqual(
                abs(
                    double_by_id[kpi_id]["measure"]
                    - default_by_id[kpi_id]["measure"] * 2
                ),
                0.0011,
            )
        for kpi_id in ("co2_proxy", "nox_proxy"):
            self.assertEqual(double_by_id[kpi_id]["measure"], default_by_id[kpi_id]["measure"])

        for invalid in (0, -1, float("inf"), float("nan"), True):
            with self.subTest(invalid=invalid), self.assertRaisesRegex(
                ValueError, "average_vehicle_occupancy"
            ):
                build_executive_kpi_block(
                    baseline,
                    measure,
                    assumptions=ExecutiveKpiAssumptions(average_vehicle_occupancy=invalid),
                )

    def test_equal_delay_rebuilds_zero_kpis_and_neutral_recommendation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            pair_outputs = generate_and_write_abay_signal_pair(
                "data/fixtures/abay/source-analytics.proxy-v1.json",
                "data/fixtures/abay/aggregate-demand.proxy-v1.json",
                Path(tmp_dir) / "pair",
                context_network_path="data/almaty_roads.geojson",
                measure_delay_s=36,
            )
            baseline = json.loads(Path(pair_outputs["baselineAnalytics"]).read_text(encoding="utf-8"))
            measure = json.loads(Path(pair_outputs["measureAnalytics"]).read_text(encoding="utf-8"))
            block = build_executive_kpi_block(baseline, measure, claim_level="proxy")
            primary = {item[0] for item in (
                ("person_hours",),
                ("corridor_speed_delta",),
                ("queue_load_proxy",),
                ("bus_reliability_proxy",),
                ("co2_proxy",),
                ("nox_proxy",),
            )}
            self.assertTrue(all(item["delta"] == 0 for item in block["kpis"] if item["id"] in primary))
            recommendation = build_recommendation(block, claim_level="proxy")
            self.assertEqual((recommendation["ruleId"], recommendation["mobilityState"]), ("M4", "M4_all_neutral"))

    def test_invalid_cost_fails_before_any_artifact_is_written(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            pair_outputs = generate_and_write_abay_signal_pair(
                "data/fixtures/abay/source-analytics.proxy-v1.json",
                "data/fixtures/abay/aggregate-demand.proxy-v1.json",
                Path(tmp_dir) / "pair",
                context_network_path="data/almaty_roads.geojson",
            )
            config = json.loads(Path("data/scenarios/dossier_abay_signal.json").read_text(encoding="utf-8"))
            config["baseline"]["analyticsPath"] = pair_outputs["baselineAnalytics"]
            config["measure"]["analyticsPath"] = pair_outputs["measureAnalytics"]
            config["pairedExperimentPath"] = pair_outputs["pairResult"]
            config["costs"]["capexKzt"] = -1
            config["outputDir"] = str(Path(tmp_dir) / "must-not-exist")
            config["runPassportPath"] = str(Path(tmp_dir) / "must-not-exist-passport.json")
            with self.assertRaisesRegex(ValueError, "capex_kzt"):
                generate_scenario_dossier(config)
            self.assertFalse(Path(config["outputDir"]).exists())
            self.assertFalse(Path(config["runPassportPath"]).exists())

    def test_active_abay_dossier_requires_selected_paired_experiment(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            config = json.loads(Path("data/scenarios/dossier_abay_signal.json").read_text(encoding="utf-8"))
            config.pop("pairedExperimentPath")
            config["outputDir"] = str(Path(tmp_dir) / "must-not-exist")
            config["runPassportPath"] = str(Path(tmp_dir) / "must-not-exist-passport.json")

            with self.assertRaisesRegex(ValueError, "pairedExperimentPath is required"):
                generate_scenario_dossier(config)

            self.assertFalse(Path(config["outputDir"]).exists())
            self.assertFalse(Path(config["runPassportPath"]).exists())

    def test_active_abay_dossier_cannot_upgrade_proxy_claim(self) -> None:
        base_config = json.loads(
            Path("data/scenarios/dossier_abay_signal.json").read_text(encoding="utf-8")
        )
        mutations = {
            "top-level": lambda config: config.__setitem__("claimLevel", "procurement-ready"),
            "baseline": lambda config: config["baseline"]["scenario"].__setitem__(
                "claim_level", "procurement-ready"
            ),
            "measure": lambda config: config["measure"]["scenario"].__setitem__(
                "claim_level", "procurement-ready"
            ),
        }
        for label, mutate in mutations.items():
            with self.subTest(label=label):
                config = deepcopy(base_config)
                mutate(config)
                with self.assertRaisesRegex(ValueError, "claim.*must be proxy"):
                    generate_scenario_dossier(config)

    def test_release_run_id_binding_rejects_split_or_unsafe_context(self) -> None:
        config = json.loads(Path("data/scenarios/dossier_abay_signal.json").read_text(encoding="utf-8"))
        config["releaseRunId"] = "release-a"
        with self.assertRaisesRegex(ValueError, "does not match"):
            generate_scenario_dossier(config, release_run_id="release-b")

        config["releaseRunId"] = "../escape"
        with self.assertRaisesRegex(ValueError, "unsafe"):
            generate_scenario_dossier(config)


def _analytics(delay: int) -> dict:
    demand = {
        "mode": "aggregate-count-v1",
        "modeledVehicleCount": 500,
        "seed": 7,
        "pattern": "normal",
        "source": {
            "relativePath": "data/fixtures/abay/aggregate-demand.proxy-v1.json",
            "sha256": "a" * 64,
            "sampleTripCount": 500,
            "originalSnapshotSha256": "b" * 64,
            "rawTripsIncluded": False,
        },
        "expansion": {"numerator": 1, "denominator": 1, "rounding": "exact-required"},
    }
    return {
        "summary": {"average_trip_time_seconds": 1600 + delay, "congestion_index": 50 + delay / 10, "total_active_vehicles": 500},
        "time_series": [{"hour": "17:00", "congestion_index": 50 + delay / 10, "avg_speed_kph": 30 - delay / 20}],
        "demandControl": demand,
    }


def _favorable_block(claim: str, economics: str) -> dict:
    block = build_executive_kpi_block(
        _analytics(36),
        _analytics(32),
        capex_kzt=100.0,
        opex_kzt_per_year=1.0,
        claim_level=claim,
    )
    by_id = kpis_by_id(block)
    if economics == "E1_incomplete":
        return block
    for kpi_id in ("capex_placeholder", "opex_placeholder", "roi_proxy", "payback_proxy"):
        by_id[kpi_id]["placeholder"] = False
        by_id[kpi_id]["available"] = True
    if economics == "E2_positive":
        by_id["capex_placeholder"]["measure"] = 100.0
        by_id["opex_placeholder"]["measure"] = 1.0
        by_id["annual_time_savings_proxy"]["measure"] = 10.0
        by_id["roi_proxy"]["measure"] = 0.09
        by_id["payback_proxy"]["measure"] = 11.111
    else:
        by_id["capex_placeholder"]["measure"] = 100.0
        by_id["opex_placeholder"]["measure"] = 20.0
        by_id["annual_time_savings_proxy"]["measure"] = 10.0
        by_id["roi_proxy"]["measure"] = -0.1
        by_id["payback_proxy"]["measure"] = 0.0
    return block


if __name__ == "__main__":
    unittest.main()
