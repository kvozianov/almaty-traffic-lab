from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
from typing import Any, TypedDict


CLAIM_LEVELS = frozenset({"demo", "proxy", "calibrated", "real-data", "procurement-ready"})
SEMANTIC_HASH_EXCLUDED_PATHS = frozenset(
    {
        "/semanticFingerprint",
        "/generatedAt",
        "/provenance/generatedAt",
        "/provenance/sourceControl",
        "/outputs",
    }
)


class PairedExperimentResult(TypedDict):
    schemaVersion: str
    modelId: str
    scenarioId: str
    corridorId: str
    claimLevel: str
    generatedAt: str
    semanticFingerprint: str
    provenance: dict[str, Any]
    experiment: dict[str, Any]
    proxyModel: dict[str, Any]
    baseline: dict[str, Any]
    measure: dict[str, Any]
    outputs: dict[str, str]


def validate_claim_level(value: str) -> str:
    if value not in CLAIM_LEVELS:
        raise ValueError(f"Unknown claim level: {value}")
    return value


def canonical_json(payload: Any) -> str:
    _reject_non_finite(payload)
    return json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"), allow_nan=False)


def semantic_fingerprint(payload: dict[str, Any]) -> str:
    semantic = deepcopy(payload)
    for pointer in sorted(SEMANTIC_HASH_EXCLUDED_PATHS, key=lambda item: item.count("/"), reverse=True):
        _remove_json_pointer(semantic, pointer)
    return hashlib.sha256(canonical_json(semantic).encode("utf-8")).hexdigest()


def validate_paired_experiment_result(payload: dict[str, Any], *, schema_path: str | Path | None = None) -> None:
    try:
        from jsonschema import Draft202012Validator, FormatChecker
        from jsonschema.exceptions import SchemaError, ValidationError
    except ImportError as exc:  # pragma: no cover - exercised by isolated dependency installation
        raise RuntimeError("jsonschema>=4.23,<5 is required to validate paired experiment contracts") from exc

    path = Path(schema_path) if schema_path is not None else _project_root() / "schemas" / "paired-experiment-result.schema.json"
    schema = json.loads(path.read_text(encoding="utf-8"))
    try:
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema, format_checker=FormatChecker()).validate(payload)
    except (SchemaError, ValidationError) as exc:
        raise ValueError(f"Invalid paired experiment result: {exc.message}") from exc
    expected = semantic_fingerprint(payload)
    if payload.get("semanticFingerprint") != expected:
        raise ValueError("Invalid paired experiment result: semanticFingerprint does not match canonical content")
    _validate_paired_semantics(payload)


def _validate_paired_semantics(payload: dict[str, Any]) -> None:
    """Enforce relationships JSON Schema cannot express across the pair."""

    if payload["claimLevel"] != "proxy":
        raise ValueError("Invalid paired experiment result: proxy-v1 claimLevel must be proxy")
    if payload["generatedAt"] != payload["provenance"]["generatedAt"]:
        raise ValueError("Invalid paired experiment result: generatedAt provenance mismatch")

    experiment = payload["experiment"]
    baseline = payload["baseline"]
    measure = payload["measure"]
    variants = (("baseline", baseline), ("measure", measure))
    if baseline["role"] != "baseline" or measure["role"] != "measure":
        raise ValueError("Invalid paired experiment result: variant roles must align with baseline and measure")

    baseline_delay = baseline["signalDelaySeconds"]
    measure_delay = measure["signalDelaySeconds"]
    _require_canonical_delay(baseline_delay, field="baseline.signalDelaySeconds")
    _require_canonical_delay(measure_delay, field="measure.signalDelaySeconds")
    delay_bindings = (
        ("experiment.baselineSignalDelaySeconds", experiment["baselineSignalDelaySeconds"], baseline_delay),
        ("experiment.measureSignalDelaySeconds", experiment["measureSignalDelaySeconds"], measure_delay),
    )
    for field, value, expected in delay_bindings:
        _require_canonical_delay(value, field=field)
        if value != expected:
            raise ValueError(f"Invalid paired experiment result: {field} does not match variant delay")

    expected_differences: list[dict[str, Any]] = []
    if baseline_delay != measure_delay:
        expected_differences.append(
            {"path": "/signalDelaySeconds", "baseline": baseline_delay, "measure": measure_delay}
        )
    if canonical_json(experiment["controlledDifferences"]) != canonical_json(expected_differences):
        raise ValueError("Invalid paired experiment result: controlledDifferences do not match variant delays")

    demand = experiment["demandControl"]
    for role, variant in variants:
        analytics = variant["analytics"]
        if canonical_json(analytics["demandControl"]) != canonical_json(demand):
            raise ValueError(
                f"Invalid paired experiment result: {role} demandControl does not match experiment"
            )
        if analytics["summary"]["total_active_vehicles"] != demand["modeledVehicleCount"]:
            raise ValueError(
                f"Invalid paired experiment result: {role} vehicle count does not match demandControl"
            )
    expansion = demand["expansion"]
    source = demand["source"]
    if (
        demand["modeledVehicleCount"] * expansion["denominator"]
        != source["sampleTripCount"] * expansion["numerator"]
    ):
        raise ValueError("Invalid paired experiment result: demandControl exact integer identity failed")
    if experiment["seed"] != demand["seed"]:
        raise ValueError("Invalid paired experiment result: experiment seed does not match demandControl")
    aggregate_ref = payload["provenance"]["aggregateDemand"]
    if aggregate_ref != {"relativePath": source["relativePath"], "sha256": source["sha256"]}:
        raise ValueError("Invalid paired experiment result: aggregate-demand provenance does not match demandControl")
    if payload["provenance"]["sourcePrimitiveVehicleCount"] != demand["sourcePrimitiveVehicleCount"]:
        raise ValueError(
            "Invalid paired experiment result: source primitive vehicle count provenance does not match demandControl"
        )

    expected_network_description = (
        "Context/provenance fingerprint only; proxy-v1 does not causally consume the road network."
    )
    network = experiment["contextNetworkFingerprint"]
    if network["description"] != expected_network_description or network["usedByModel"] is not False:
        raise ValueError("Invalid paired experiment result: network fingerprint must remain context-only")
    base_series_fingerprint = experiment["baseSeriesFingerprint"]
    for role, variant in variants:
        analytics_experiment = variant["analytics"]["pairedExperiment"]
        expected_delay = baseline_delay if role == "baseline" else measure_delay
        _require_canonical_delay(
            analytics_experiment["signalDelaySeconds"],
            field=f"{role}.analytics.pairedExperiment.signalDelaySeconds",
        )
        if analytics_experiment["signalDelaySeconds"] != expected_delay:
            raise ValueError(
                f"Invalid paired experiment result: {role} analytics delay does not match variant"
            )
        if analytics_experiment["seed"] != experiment["seed"]:
            raise ValueError(f"Invalid paired experiment result: {role} analytics seed mismatch")
        if analytics_experiment["baseSeriesFingerprint"] != base_series_fingerprint:
            raise ValueError(
                f"Invalid paired experiment result: {role} base-series fingerprint mismatch"
            )
        if canonical_json(analytics_experiment["contextNetworkFingerprint"]) != canonical_json(network):
            raise ValueError(
                f"Invalid paired experiment result: {role} network fingerprint mismatch"
            )
        for identity_field in ("schemaVersion", "modelId", "scenarioId"):
            if analytics_experiment[identity_field] != payload[identity_field]:
                raise ValueError(
                    f"Invalid paired experiment result: {role} analytics {identity_field} mismatch"
                )

    baseline_analytics = baseline["analytics"]
    measure_analytics = measure["analytics"]
    normalized_base = deepcopy(baseline_analytics)
    normalized_base.pop("pairedExperiment")
    recomputed_base_fingerprint = hashlib.sha256(
        canonical_json(normalized_base).encode("utf-8")
    ).hexdigest()
    if recomputed_base_fingerprint != base_series_fingerprint:
        raise ValueError("Invalid paired experiment result: base-series fingerprint does not match baseline")
    for field in ("node_throughput", "ml_forecast", "demandControl"):
        if canonical_json(baseline_analytics[field]) != canonical_json(measure_analytics[field]):
            raise ValueError(f"Invalid paired experiment result: unchanged analytics field differs: {field}")
    if len(baseline_analytics["time_series"]) != len(measure_analytics["time_series"]):
        raise ValueError("Invalid paired experiment result: time-series lengths differ")
    if [item["hour"] for item in baseline_analytics["time_series"]] != [
        item["hour"] for item in measure_analytics["time_series"]
    ]:
        raise ValueError("Invalid paired experiment result: time-series hours differ")

    bounds = payload["proxyModel"]["bounds"]
    expected_bounds = {
        "signalDelaySeconds": {"minimum": 0, "maximum": 120},
        "affectedSignalsPerTrip": {"minimum": 1, "maximum": 20},
        "realizationFactor": {"minimum": 0, "maximum": 1},
        "congestionIndex": {"minimum": 0, "maximum": 100},
        "averageSpeedKph": {"minimum": 5, "maximum": 80},
    }
    if canonical_json(bounds) != canonical_json(expected_bounds):
        raise ValueError("Invalid paired experiment result: proxy bounds do not match proxy-v1")

    computed = payload["proxyModel"]["computed"]
    affected = computed["affectedSignalsPerTrip"]
    realization = computed["realizationFactor"]
    _require_canonical_integral_number(
        realization,
        field="proxyModel.computed.realizationFactor",
    )
    required_no_scaling_limitation = (
        "Trip-time, congestion, speed, throughput, and forecast primitives are reused without "
        "demand-response scaling from the source primitive vehicle count to the modeled vehicle count."
    )
    if required_no_scaling_limitation not in payload["proxyModel"]["limitations"]:
        raise ValueError(
            "Invalid paired experiment result: demand-response scaling limitation is required"
        )
    expected_baseline_component = affected * baseline_delay * realization
    expected_measure_component = affected * measure_delay * realization
    _require_close(
        computed["baselineSignalComponentSeconds"],
        expected_baseline_component,
        field="proxyModel.computed.baselineSignalComponentSeconds",
    )
    _require_close(
        computed["measureSignalComponentSeconds"],
        expected_measure_component,
        field="proxyModel.computed.measureSignalComponentSeconds",
    )
    expected_baseline_trip = computed["runningTimeSeconds"] + expected_baseline_component
    expected_measure_trip = computed["runningTimeSeconds"] + expected_measure_component
    _require_close(
        computed["baselineTripTimeSeconds"],
        expected_baseline_trip,
        field="proxyModel.computed.baselineTripTimeSeconds",
    )
    _require_close(
        computed["measureTripTimeSeconds"],
        expected_measure_trip,
        field="proxyModel.computed.measureTripTimeSeconds",
    )
    _require_close(computed["baselineRatio"], 1.0, field="proxyModel.computed.baselineRatio")
    expected_measure_ratio = expected_measure_trip / expected_baseline_trip
    _require_close(
        computed["measureRatio"],
        expected_measure_ratio,
        field="proxyModel.computed.measureRatio",
    )
    if baseline_analytics["summary"]["average_trip_time_seconds"] != round(expected_baseline_trip, 2):
        raise ValueError("Invalid paired experiment result: baseline trip time does not match proxy formula")
    if measure_analytics["summary"]["average_trip_time_seconds"] != round(expected_measure_trip, 2):
        raise ValueError("Invalid paired experiment result: measure trip time does not match proxy formula")

    _validate_transformed_analytics(
        baseline_analytics,
        measure_analytics,
        ratio=expected_measure_ratio,
    )
    _validate_clamp_paths(
        baseline_analytics["pairedExperiment"]["clampedFields"],
        _expected_clamp_paths(baseline_analytics, ratio=1.0),
        role="baseline",
    )
    _validate_clamp_paths(
        measure_analytics["pairedExperiment"]["clampedFields"],
        _expected_clamp_paths(baseline_analytics, ratio=expected_measure_ratio),
        role="measure",
    )
    if baseline_delay == measure_delay and canonical_json(baseline_analytics) != canonical_json(measure_analytics):
        raise ValueError("Invalid paired experiment result: equal delays must produce canonical analytics identity")


def _require_canonical_delay(value: Any, *, field: str) -> None:
    _require_canonical_integral_number(value, field=field)


def _require_canonical_integral_number(value: Any, *, field: str) -> None:
    if isinstance(value, float) and value.is_integer():
        raise ValueError(f"Invalid paired experiment result: {field} uses a non-canonical integral float")


def _require_close(actual: Any, expected: float, *, field: str) -> None:
    if not math.isclose(float(actual), float(expected), rel_tol=1e-12, abs_tol=1e-9):
        raise ValueError(f"Invalid paired experiment result: {field} does not match proxy formula")


def _validate_transformed_analytics(
    baseline: dict[str, Any], measure: dict[str, Any], *, ratio: float
) -> None:
    baseline_summary_congestion = float(baseline["summary"]["congestion_index"])
    expected_summary_congestion = round(min(100.0, max(0.0, baseline_summary_congestion * ratio)), 2)
    _require_serialized_near(
        measure["summary"]["congestion_index"],
        expected_summary_congestion,
        precision=2,
        field="measure.summary.congestion_index",
    )
    for index, (baseline_point, measure_point) in enumerate(
        zip(baseline["time_series"], measure["time_series"], strict=True)
    ):
        expected_congestion = round(
            min(100.0, max(0.0, float(baseline_point["congestion_index"]) * ratio)), 2
        )
        expected_speed = round(
            min(80.0, max(5.0, float(baseline_point["avg_speed_kph"]) / ratio)), 1
        )
        _require_serialized_near(
            measure_point["congestion_index"],
            expected_congestion,
            precision=2,
            field=f"measure.time_series[{index}].congestion_index",
        )
        _require_serialized_near(
            measure_point["avg_speed_kph"],
            expected_speed,
            precision=1,
            field=f"measure.time_series[{index}].avg_speed_kph",
        )


def _require_serialized_near(actual: Any, expected: float, *, precision: int, field: str) -> None:
    if not math.isclose(float(actual), expected, rel_tol=0.0, abs_tol=10 ** (-(precision + 9))):
        raise ValueError(f"Invalid paired experiment result: {field} does not match shared base series")


def _expected_clamp_paths(baseline: dict[str, Any], *, ratio: float) -> list[str]:
    expected: list[str] = []
    raw_summary_congestion = float(baseline["summary"]["congestion_index"]) * ratio
    if raw_summary_congestion < 0.0 or raw_summary_congestion > 100.0:
        expected.append("/summary/congestion_index")
    for index, point in enumerate(baseline["time_series"]):
        raw_congestion = float(point["congestion_index"]) * ratio
        if raw_congestion < 0.0 or raw_congestion > 100.0:
            expected.append(f"/time_series/{index}/congestion_index")
        raw_speed = float(point["avg_speed_kph"]) / ratio
        if raw_speed < 5.0 or raw_speed > 80.0:
            expected.append(f"/time_series/{index}/avg_speed_kph")
    return expected


def _validate_clamp_paths(paths: list[str], expected: list[str], *, role: str) -> None:
    if paths != expected:
        raise ValueError(
            f"Invalid paired experiment result: {role} clampedFields do not match recomputed clamp metadata"
        )


def _remove_json_pointer(payload: dict[str, Any], pointer: str) -> None:
    if not pointer.startswith("/"):
        raise ValueError(f"Invalid JSON pointer: {pointer}")
    parts = [part.replace("~1", "/").replace("~0", "~") for part in pointer[1:].split("/")]
    current: Any = payload
    for part in parts[:-1]:
        if not isinstance(current, dict) or part not in current:
            return
        current = current[part]
    if isinstance(current, dict):
        current.pop(parts[-1], None)


def _reject_non_finite(value: Any, *, path: str = "$") -> None:
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError(f"Non-finite number at {path}")
    if isinstance(value, dict):
        for key, item in value.items():
            _reject_non_finite(item, path=f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _reject_non_finite(item, path=f"{path}[{index}]")


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]
