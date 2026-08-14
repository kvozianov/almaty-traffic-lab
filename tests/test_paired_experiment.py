from __future__ import annotations

from copy import deepcopy
import json
import math
import tempfile
import unittest
from pathlib import Path

from traffic_sim.contracts import (
    SEMANTIC_HASH_EXCLUDED_PATHS,
    canonical_json,
    semantic_fingerprint,
    validate_paired_experiment_result,
)
from traffic_sim.paired_experiment import (
    generate_abay_signal_pair,
    generate_and_write_abay_signal_pair,
)


SOURCE_ANALYTICS = Path("data/fixtures/abay/source-analytics.proxy-v1.json")
AGGREGATE_DEMAND = Path("data/fixtures/abay/aggregate-demand.proxy-v1.json")


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class PairedExperimentTests(unittest.TestCase):
    def _pair(self, **overrides: object) -> dict:
        demand = _load(AGGREGATE_DEMAND)
        return generate_abay_signal_pair(
            _load(SOURCE_ANALYTICS),
            demand,
            source_analytics_ref={"relativePath": str(SOURCE_ANALYTICS), "sha256": _sha256(SOURCE_ANALYTICS)},
            aggregate_demand_ref={"relativePath": str(AGGREGATE_DEMAND), "sha256": _sha256(AGGREGATE_DEMAND)},
            context_network_fingerprint="a" * 64,
            **overrides,
        )

    def test_active_pair_is_36_to_32_with_exact_aggregate_demand(self) -> None:
        pair = self._pair()
        baseline = pair["baseline"]
        measure = pair["measure"]

        self.assertEqual(pair["modelId"], "abay-signal-delay-proxy-v1")
        self.assertEqual(baseline["signalDelaySeconds"], 36)
        self.assertEqual(measure["signalDelaySeconds"], 32)
        self.assertEqual(pair["experiment"]["controlledDifferences"], [
            {"path": "/signalDelaySeconds", "baseline": 36, "measure": 32}
        ])
        self.assertEqual(baseline["analytics"]["demandControl"], measure["analytics"]["demandControl"])
        demand = baseline["analytics"]["demandControl"]
        self.assertEqual(demand["modeledVehicleCount"], 500)
        self.assertEqual(demand["seed"], 7)
        self.assertEqual(demand["sourcePrimitiveVehicleCount"], 1950)
        self.assertEqual(pair["provenance"]["sourcePrimitiveVehicleCount"], 1950)
        self.assertEqual(demand["source"]["sampleTripCount"], 500)
        self.assertEqual(
            demand["source"]["originalSnapshotSha256"],
            "b7ea1bfeef889e695ccfbbf4cb115de51b330b064601c89184677060e5f6eab3",
        )
        self.assertEqual(demand["expansion"], {"numerator": 1, "denominator": 1, "rounding": "exact-required"})
        self.assertEqual(
            demand["modeledVehicleCount"] * demand["expansion"]["denominator"],
            demand["source"]["sampleTripCount"] * demand["expansion"]["numerator"],
        )
        self.assertFalse(demand["source"]["rawTripsIncluded"])
        self.assertFalse(pair["experiment"]["contextNetworkFingerprint"]["usedByModel"])
        self.assertIn(
            "Trip-time, congestion, speed, throughput, and forecast primitives are reused without demand-response scaling from the source primitive vehicle count to the modeled vehicle count.",
            pair["proxyModel"]["limitations"],
        )

    def test_integral_realization_boundaries_have_one_semantic_representation(self) -> None:
        for boundary in (0, 1):
            with self.subTest(boundary=boundary):
                integer_pair = self._pair(realization_factor=boundary)
                float_pair = self._pair(realization_factor=float(boundary))
                self.assertEqual(
                    integer_pair["semanticFingerprint"],
                    float_pair["semanticFingerprint"],
                )
                self.assertIsInstance(
                    integer_pair["proxyModel"]["computed"]["realizationFactor"], int
                )
                self.assertIsInstance(
                    float_pair["proxyModel"]["computed"]["realizationFactor"], int
                )

                forged = deepcopy(integer_pair)
                forged["proxyModel"]["computed"]["realizationFactor"] = float(boundary)
                forged["semanticFingerprint"] = semantic_fingerprint(forged)
                with self.assertRaisesRegex(ValueError, "non-canonical integral float"):
                    validate_paired_experiment_result(forged)

    def test_formula_sign_precision_and_unchanged_fields(self) -> None:
        pair = self._pair()
        baseline = pair["baseline"]["analytics"]
        measure = pair["measure"]["analytics"]
        computed = pair["proxyModel"]["computed"]

        self.assertAlmostEqual(computed["baselineSignalComponentSeconds"], 4 * 36 * 0.55)
        self.assertAlmostEqual(computed["measureSignalComponentSeconds"], 4 * 32 * 0.55)
        self.assertAlmostEqual(computed["runningTimeSeconds"], 1663.46 - 4 * 36 * 0.55)
        self.assertEqual(baseline["summary"]["average_trip_time_seconds"], 1663.46)
        self.assertEqual(measure["summary"]["average_trip_time_seconds"], 1654.66)
        self.assertLess(measure["summary"]["congestion_index"], baseline["summary"]["congestion_index"])
        self.assertGreater(
            sum(item["avg_speed_kph"] for item in measure["time_series"]),
            sum(item["avg_speed_kph"] for item in baseline["time_series"]),
        )
        self.assertEqual(measure["ml_forecast"], baseline["ml_forecast"])
        self.assertEqual(measure["node_throughput"], baseline["node_throughput"])
        self.assertEqual(pair["experiment"]["unchangedFields"], [
            "/analytics/ml_forecast",
            "/analytics/node_throughput",
            "/analytics/demandControl",
        ])
        for analytics in (baseline, measure):
            self.assertGreaterEqual(analytics["summary"]["congestion_index"], 0)
            self.assertLessEqual(analytics["summary"]["congestion_index"], 100)
            self.assertTrue(all(0 <= row["congestion_index"] <= 100 for row in analytics["time_series"]))
            self.assertTrue(all(5 <= row["avg_speed_kph"] <= 80 for row in analytics["time_series"]))

    def test_equal_delay_is_semantic_identity_and_zero_control(self) -> None:
        for measure_delay in (36, 36.0):
            with self.subTest(measure_delay=measure_delay):
                pair = self._pair(measure_delay_s=measure_delay)
                self.assertEqual(pair["baseline"]["analytics"], pair["measure"]["analytics"])
                self.assertEqual(
                    canonical_json(pair["baseline"]["analytics"]),
                    canonical_json(pair["measure"]["analytics"]),
                )
                self.assertEqual(pair["experiment"]["controlledDifferences"], [])

    def test_plus_minus_four_seconds_is_reversible_from_same_primitives(self) -> None:
        slower = self._pair(measure_delay_s=40)
        faster = self._pair(measure_delay_s=32)
        t0 = slower["proxyModel"]["computed"]["baselineTripTimeSeconds"]
        plus = slower["proxyModel"]["computed"]["measureTripTimeSeconds"] - t0
        minus = faster["proxyModel"]["computed"]["measureTripTimeSeconds"] - t0
        self.assertEqual(plus, -minus)
        self.assertGreater(slower["measure"]["analytics"]["summary"]["congestion_index"], slower["baseline"]["analytics"]["summary"]["congestion_index"])
        self.assertLess(faster["measure"]["analytics"]["summary"]["congestion_index"], faster["baseline"]["analytics"]["summary"]["congestion_index"])

    def test_semantic_fingerprint_is_deterministic_and_schema_is_closed(self) -> None:
        first = self._pair()
        second = self._pair()
        self.assertEqual(
            SEMANTIC_HASH_EXCLUDED_PATHS,
            frozenset({
                "/semanticFingerprint",
                "/generatedAt",
                "/provenance/generatedAt",
                "/provenance/sourceControl",
                "/outputs",
            }),
        )
        self.assertEqual(first["semanticFingerprint"], second["semanticFingerprint"])
        validate_paired_experiment_result(first)
        invalid = deepcopy(first)
        invalid["experiment"]["unregisteredTimestamp"] = "2026-08-12T00:00:00Z"
        with self.assertRaises(ValueError):
            validate_paired_experiment_result(invalid)

    def test_invalid_model_inputs_and_non_exact_demand_are_rejected(self) -> None:
        for kwargs in (
            {"baseline_delay_s": -1},
            {"measure_delay_s": 121},
            {"affected_signals_per_trip": 0},
            {"affected_signals_per_trip": 21},
            {"realization_factor": -0.1},
            {"realization_factor": 1.1},
        ):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                self._pair(**kwargs)

        source = _load(SOURCE_ANALYTICS)
        demand = _load(AGGREGATE_DEMAND)
        seeded_demand = deepcopy(demand)
        seeded_demand["seed"] = 7
        with self.assertRaisesRegex(ValueError, "unsupported fields.*seed"):
            generate_abay_signal_pair(
                source,
                seeded_demand,
                source_analytics_ref={"relativePath": str(SOURCE_ANALYTICS), "sha256": "b" * 64},
                aggregate_demand_ref={"relativePath": str(AGGREGATE_DEMAND), "sha256": "c" * 64},
                context_network_fingerprint="a" * 64,
            )

        demand["expansion"] = {"numerator": 3, "denominator": 2, "rounding": "exact-required"}
        with self.assertRaisesRegex(ValueError, "exact integer identity"):
            generate_abay_signal_pair(
                source,
                demand,
                source_analytics_ref={"relativePath": str(SOURCE_ANALYTICS), "sha256": "b" * 64},
                aggregate_demand_ref={"relativePath": str(AGGREGATE_DEMAND), "sha256": "c" * 64},
                context_network_fingerprint="a" * 64,
            )

        broken = deepcopy(source)
        broken["summary"]["average_trip_time_seconds"] = 1
        with self.assertRaisesRegex(ValueError, "running time"):
            generate_abay_signal_pair(
                broken,
                _load(AGGREGATE_DEMAND),
                source_analytics_ref={"relativePath": str(SOURCE_ANALYTICS), "sha256": "b" * 64},
                aggregate_demand_ref={"relativePath": str(AGGREGATE_DEMAND), "sha256": "c" * 64},
                context_network_fingerprint="a" * 64,
            )

        overprecise = deepcopy(source)
        overprecise["summary"]["congestion_index"] = 55.591
        with self.assertRaisesRegex(ValueError, "serialized to 2 decimal places"):
            generate_abay_signal_pair(
                overprecise,
                _load(AGGREGATE_DEMAND),
                source_analytics_ref={"relativePath": str(SOURCE_ANALYTICS), "sha256": "b" * 64},
                aggregate_demand_ref={"relativePath": str(AGGREGATE_DEMAND), "sha256": "c" * 64},
                context_network_fingerprint="a" * 64,
            )

    def test_proxy_model_cannot_self_upgrade_claim_level(self) -> None:
        for claim_level in ("demo", "calibrated", "real-data", "procurement-ready"):
            with self.subTest(claim_level=claim_level), self.assertRaisesRegex(
                ValueError, "claim_level must be proxy"
            ):
                self._pair(claim_level=claim_level)

    def test_semantic_validator_rejects_cross_field_tampering(self) -> None:
        mutations = {
            "experiment demand differs from analytics": lambda pair: pair["experiment"][
                "demandControl"
            ].__setitem__("modeledVehicleCount", 501),
            "experiment delay differs from variant": lambda pair: pair["experiment"].__setitem__(
                "baselineSignalDelaySeconds", 35
            ),
            "computed formula is forged": lambda pair: pair["proxyModel"]["computed"].__setitem__(
                "measureTripTimeSeconds", 999
            ),
            "embedded base series differs": lambda pair: pair["measure"]["analytics"][
                "pairedExperiment"
            ].__setitem__("baseSeriesFingerprint", "b" * 64),
            "unchanged analytics differs": lambda pair: pair["measure"]["analytics"][
                "node_throughput"
            ].append({"node_id": "forged", "vehicles_per_hour": 1, "status": "forged"}),
            "source primitive provenance differs from demand control": lambda pair: pair[
                "provenance"
            ].__setitem__("sourcePrimitiveVehicleCount", 1949),
        }
        for label, mutate in mutations.items():
            with self.subTest(label=label):
                pair = self._pair()
                mutate(pair)
                pair["semanticFingerprint"] = semantic_fingerprint(pair)
                with self.assertRaises(ValueError):
                    validate_paired_experiment_result(pair)

    def test_clamp_metadata_is_recomputed_and_boundary_numbers_remain_canonical(self) -> None:
        boundary_source = _load(SOURCE_ANALYTICS)
        boundary_source["summary"]["congestion_index"] = 0
        for index, point in enumerate(boundary_source["time_series"]):
            point["congestion_index"] = 0 if index % 2 == 0 else 100
            point["avg_speed_kph"] = 5 if index % 2 == 0 else 80

        boundary_pair = generate_abay_signal_pair(
            boundary_source,
            _load(AGGREGATE_DEMAND),
            source_analytics_ref={"relativePath": str(SOURCE_ANALYTICS), "sha256": "b" * 64},
            aggregate_demand_ref={"relativePath": str(AGGREGATE_DEMAND), "sha256": "c" * 64},
            context_network_fingerprint="a" * 64,
            measure_delay_s=36,
        )
        validate_paired_experiment_result(boundary_pair)
        self.assertEqual(
            boundary_pair["baseline"]["analytics"]["pairedExperiment"]["clampedFields"], []
        )
        self.assertEqual(
            boundary_pair["measure"]["analytics"]["pairedExperiment"]["clampedFields"], []
        )

        clamped_source = _load(SOURCE_ANALYTICS)
        clamped_source["summary"]["congestion_index"] = 100
        for point in clamped_source["time_series"]:
            point["congestion_index"] = 100
            point["avg_speed_kph"] = 40
        pair = generate_abay_signal_pair(
            clamped_source,
            _load(AGGREGATE_DEMAND),
            source_analytics_ref={"relativePath": str(SOURCE_ANALYTICS), "sha256": "b" * 64},
            aggregate_demand_ref={"relativePath": str(AGGREGATE_DEMAND), "sha256": "c" * 64},
            context_network_fingerprint="a" * 64,
            measure_delay_s=40,
        )
        validate_paired_experiment_result(pair)
        self.assertEqual(pair["baseline"]["analytics"]["pairedExperiment"]["clampedFields"], [])
        self.assertEqual(
            len(pair["measure"]["analytics"]["pairedExperiment"]["clampedFields"]),
            25,
        )

        forged = deepcopy(pair)
        forged["measure"]["analytics"]["pairedExperiment"]["clampedFields"] = []
        forged["semanticFingerprint"] = semantic_fingerprint(forged)
        with self.assertRaisesRegex(ValueError, "recomputed clamp metadata"):
            validate_paired_experiment_result(forged)

    def test_source_normalization_strips_stale_blocks_and_writer_validates_first(self) -> None:
        source = _load(SOURCE_ANALYTICS)
        source["executive_kpis"] = {"stale": True}
        source["executiveKpis"] = {"stale": True}
        source["pairedExperiment"] = {"stale": True}
        source["generatedAt"] = "stale"
        source["provenance"] = {"generatedAt": "stale"}
        source["outputs"] = {"stale": True}
        pair = generate_abay_signal_pair(
            source,
            _load(AGGREGATE_DEMAND),
            source_analytics_ref={"relativePath": str(SOURCE_ANALYTICS), "sha256": "b" * 64},
            aggregate_demand_ref={"relativePath": str(AGGREGATE_DEMAND), "sha256": "c" * 64},
            context_network_fingerprint="a" * 64,
        )
        analytics = pair["baseline"]["analytics"]
        self.assertNotIn("executive_kpis", analytics)
        self.assertNotIn("executiveKpis", analytics)
        self.assertNotIn("generatedAt", analytics)
        self.assertNotIn("provenance", analytics)
        self.assertNotIn("outputs", analytics)
        self.assertEqual(analytics["pairedExperiment"]["modelId"], "abay-signal-delay-proxy-v1")

        with tempfile.TemporaryDirectory() as tmp_dir:
            outputs = generate_and_write_abay_signal_pair(
                SOURCE_ANALYTICS,
                AGGREGATE_DEMAND,
                tmp_dir,
                context_network_path="data/almaty_roads.geojson",
            )
            self.assertEqual(set(outputs), {"pairResult", "baselineAnalytics", "measureAnalytics"})
            written_pair = _load(Path(outputs["pairResult"]))
            validate_paired_experiment_result(written_pair)
            self.assertEqual(written_pair["outputs"], outputs)

    def test_writer_separates_physical_paths_from_logical_contract_refs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            outputs = generate_and_write_abay_signal_pair(
                SOURCE_ANALYTICS,
                AGGREGATE_DEMAND,
                Path(tmp_dir) / ".staging" / "pair",
                context_network_path="data/almaty_roads.geojson",
                logical_output_dir="artifacts/pair",
            )
            self.assertTrue(all(Path(path).is_file() for path in outputs.values()))
            pair = _load(Path(outputs["pairResult"]))
            self.assertEqual(pair["outputs"], {
                "pairResult": "artifacts/pair/paired-experiment.json",
                "baselineAnalytics": "artifacts/pair/baseline.analytics.json",
                "measureAnalytics": "artifacts/pair/measure.analytics.json",
            })
            self.assertNotIn(".staging", json.dumps(pair))


def _sha256(path: Path) -> str:
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest()


if __name__ == "__main__":
    unittest.main()
