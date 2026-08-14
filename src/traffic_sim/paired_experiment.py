from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Mapping

from .contracts import (
    PairedExperimentResult,
    canonical_json,
    semantic_fingerprint,
    validate_claim_level,
    validate_paired_experiment_result,
)


SCHEMA_VERSION = "1.0.0"
MODEL_ID = "abay-signal-delay-proxy-v1"
SCENARIO_ID = "abay-signal-retiming"
CORRIDOR_ID = "abay"
DEFAULT_BASELINE_DELAY_S = 36
DEFAULT_MEASURE_DELAY_S = 32
DEFAULT_AFFECTED_SIGNALS_PER_TRIP = 4
DEFAULT_REALIZATION_FACTOR = 0.55


def generate_abay_signal_pair(
    source_analytics: Mapping[str, Any],
    aggregate_demand: Mapping[str, Any],
    *,
    source_analytics_ref: Mapping[str, str],
    aggregate_demand_ref: Mapping[str, str],
    context_network_fingerprint: str,
    seed: int = 7,
    baseline_delay_s: float = DEFAULT_BASELINE_DELAY_S,
    measure_delay_s: float = DEFAULT_MEASURE_DELAY_S,
    affected_signals_per_trip: int = DEFAULT_AFFECTED_SIGNALS_PER_TRIP,
    realization_factor: float = DEFAULT_REALIZATION_FACTOR,
    claim_level: str = "proxy",
    generated_at: str | None = None,
    schema_path: str | Path | None = None,
) -> PairedExperimentResult:
    """Build one controlled Abay pair from shared immutable aggregate primitives.

    This adapter is intentionally not a network simulator. It changes only the
    transparent signal-delay sensitivity input and regenerates both variants
    directly from the same normalized source snapshot.
    """

    validate_claim_level(claim_level)
    if claim_level != "proxy":
        raise ValueError("abay-signal-delay-proxy-v1 claim_level must be proxy")
    _validate_number("baseline_delay_s", baseline_delay_s, minimum=0, maximum=120)
    _validate_number("measure_delay_s", measure_delay_s, minimum=0, maximum=120)
    baseline_delay_s = _normalized_contract_number(baseline_delay_s)
    measure_delay_s = _normalized_contract_number(measure_delay_s)
    if isinstance(affected_signals_per_trip, bool) or not isinstance(affected_signals_per_trip, int):
        raise ValueError("affected_signals_per_trip must be an integer in 1..20")
    if not 1 <= affected_signals_per_trip <= 20:
        raise ValueError("affected_signals_per_trip must be in 1..20")
    _validate_number("realization_factor", realization_factor, minimum=0, maximum=1)
    realization_factor = _normalized_contract_number(realization_factor)
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("seed must be an integer")
    _validate_sha256(context_network_fingerprint, field="context_network_fingerprint")
    source_ref = _artifact_ref(source_analytics_ref, field="source_analytics_ref")
    demand_ref = _artifact_ref(aggregate_demand_ref, field="aggregate_demand_ref")
    demand_control = _build_demand_control(aggregate_demand, demand_ref=demand_ref, seed=seed)
    source_primitive_vehicle_count = _source_primitive_vehicle_count(source_analytics)
    demand_control["sourcePrimitiveVehicleCount"] = source_primitive_vehicle_count
    normalized = _normalize_source_analytics(source_analytics, demand_control=demand_control)
    base_series_fingerprint = hashlib.sha256(canonical_json(normalized).encode("utf-8")).hexdigest()

    baseline_trip_time = _finite_positive(
        normalized["summary"]["average_trip_time_seconds"],
        field="summary.average_trip_time_seconds",
    )
    baseline_signal_component = affected_signals_per_trip * float(baseline_delay_s) * float(realization_factor)
    measure_signal_component = affected_signals_per_trip * float(measure_delay_s) * float(realization_factor)
    running_time = baseline_trip_time - baseline_signal_component
    if not math.isfinite(running_time) or running_time <= 0:
        raise ValueError("Proxy running time must be finite and greater than zero")
    denominator = running_time + baseline_signal_component
    if not math.isfinite(denominator) or denominator <= 0:
        raise ValueError("Baseline trip-time denominator must be finite and greater than zero")
    measure_trip_time = running_time + measure_signal_component
    if not math.isfinite(measure_trip_time) or measure_trip_time <= 0:
        raise ValueError("Measure trip time must be finite and greater than zero")
    baseline_ratio = denominator / denominator
    measure_ratio = measure_trip_time / denominator
    if not math.isfinite(measure_ratio) or measure_ratio <= 0:
        raise ValueError("Measure trip-time ratio must be finite and greater than zero")

    network_context = {
        "sha256": context_network_fingerprint,
        "usedByModel": False,
        "description": "Context/provenance fingerprint only; proxy-v1 does not causally consume the road network.",
    }
    baseline_analytics = _variant_analytics(
        normalized,
        delay_s=baseline_delay_s,
        trip_time_s=denominator,
        ratio=baseline_ratio,
        seed=seed,
        base_series_fingerprint=base_series_fingerprint,
        network_context=network_context,
    )
    measure_analytics = _variant_analytics(
        normalized,
        delay_s=measure_delay_s,
        trip_time_s=measure_trip_time,
        ratio=measure_ratio,
        seed=seed,
        base_series_fingerprint=base_series_fingerprint,
        network_context=network_context,
    )
    if baseline_analytics["demandControl"] != measure_analytics["demandControl"]:
        raise ValueError("Baseline and measure demandControl must be canonical deep-equal")
    if baseline_analytics["ml_forecast"] != measure_analytics["ml_forecast"]:
        raise ValueError("ml_forecast must remain unchanged in proxy-v1")
    if baseline_analytics["node_throughput"] != measure_analytics["node_throughput"]:
        raise ValueError("node_throughput must remain unchanged in proxy-v1")

    controlled_differences: list[dict[str, Any]] = []
    if float(baseline_delay_s) != float(measure_delay_s):
        controlled_differences.append(
            {"path": "/signalDelaySeconds", "baseline": baseline_delay_s, "measure": measure_delay_s}
        )
    timestamp = generated_at or datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    result: PairedExperimentResult = {
        "schemaVersion": SCHEMA_VERSION,
        "modelId": MODEL_ID,
        "scenarioId": SCENARIO_ID,
        "corridorId": CORRIDOR_ID,
        "claimLevel": claim_level,
        "generatedAt": timestamp,
        "semanticFingerprint": "0" * 64,
        "provenance": {
            "generatedAt": timestamp,
            "sourceControl": {},
            "sourceAnalytics": source_ref,
            "aggregateDemand": demand_ref,
            "sourcePrimitiveVehicleCount": source_primitive_vehicle_count,
        },
        "experiment": {
            "seed": seed,
            "baselineSignalDelaySeconds": baseline_delay_s,
            "measureSignalDelaySeconds": measure_delay_s,
            "controlledDifferences": controlled_differences,
            "unchangedFields": [
                "/analytics/ml_forecast",
                "/analytics/node_throughput",
                "/analytics/demandControl",
            ],
            "demandControl": deepcopy(demand_control),
            "baseSeriesFingerprint": base_series_fingerprint,
            "contextNetworkFingerprint": deepcopy(network_context),
        },
        "proxyModel": {
            "formula": {
                "signalComponent": "S(d) = affected_signals_per_trip * d * realization_factor",
                "runningTime": "R = baseline.average_trip_time_seconds - S(baseline_delay_s)",
                "tripTime": "T(d) = R + S(d)",
                "ratio": "q(d) = T(d) / T(baseline_delay_s)",
            },
            "units": {
                "signalDelay": "seconds",
                "tripTime": "seconds",
                "congestionIndex": "0-100",
                "averageSpeed": "km/h",
            },
            "bounds": {
                "signalDelaySeconds": {"minimum": 0, "maximum": 120},
                "affectedSignalsPerTrip": {"minimum": 1, "maximum": 20},
                "realizationFactor": {"minimum": 0, "maximum": 1},
                "congestionIndex": {"minimum": 0, "maximum": 100},
                "averageSpeedKph": {"minimum": 5, "maximum": 80},
            },
            "rounding": {
                "averageTripTimeDecimals": 2,
                "congestionIndexDecimals": 2,
                "averageSpeedDecimals": 1,
                "kpiDecimals": 3,
                "calculationRule": "calculate with unrounded finite floats, then serialize at field precision",
            },
            "assumptions": [
                f"{affected_signals_per_trip} affected signals per trip is a proxy assumption, not an OD-derived fact.",
                f"The realization factor {realization_factor} is a bounded proxy sensitivity assumption.",
                f"The active {baseline_delay_s}s and {measure_delay_s}s inputs are sensitivity values, not observed controller timings.",
                "Source trip, congestion, and speed primitives are admitted at the declared 2/2/1-decimal contract precision before unrounded proxy calculations.",
            ],
            "limitations": [
                "Proxy-v1 does not model routing, queues, junction throughput, signal coordination, or controller feasibility.",
                "The network fingerprint is contextual provenance only and is not used by the model.",
                "Aggregate demand equality does not establish trip-level or OD equivalence.",
                "Trip-time, congestion, speed, throughput, and forecast primitives are reused without demand-response scaling from the source primitive vehicle count to the modeled vehicle count.",
            ],
            "computed": {
                "affectedSignalsPerTrip": affected_signals_per_trip,
                "realizationFactor": realization_factor,
                "baselineSignalComponentSeconds": baseline_signal_component,
                "measureSignalComponentSeconds": measure_signal_component,
                "runningTimeSeconds": running_time,
                "baselineTripTimeSeconds": denominator,
                "measureTripTimeSeconds": measure_trip_time,
                "baselineRatio": baseline_ratio,
                "measureRatio": measure_ratio,
            },
        },
        "baseline": {
            "role": "baseline",
            "signalDelaySeconds": baseline_delay_s,
            "analytics": baseline_analytics,
        },
        "measure": {
            "role": "measure",
            "signalDelaySeconds": measure_delay_s,
            "analytics": measure_analytics,
        },
        "outputs": {},
    }
    result["semanticFingerprint"] = semantic_fingerprint(result)
    validate_paired_experiment_result(result, schema_path=schema_path)
    return result


def write_paired_experiment(
    result: PairedExperimentResult,
    output_dir: str | Path,
    *,
    logical_output_dir: str | None = None,
    schema_path: str | Path | None = None,
) -> dict[str, str]:
    """Validate and write all pair artifacts below one caller-selected directory."""

    destination = Path(output_dir)
    outputs = {
        "pairResult": str(destination / "paired-experiment.json"),
        "baselineAnalytics": str(destination / "baseline.analytics.json"),
        "measureAnalytics": str(destination / "measure.analytics.json"),
    }
    serialized_outputs = outputs
    if logical_output_dir is not None:
        logical_root = Path(logical_output_dir)
        if logical_root.is_absolute() or ".." in logical_root.parts or ".staging" in logical_root.parts:
            raise ValueError("logical_output_dir must be a safe run-relative path")
        serialized_outputs = {
            "pairResult": (logical_root / "paired-experiment.json").as_posix(),
            "baselineAnalytics": (logical_root / "baseline.analytics.json").as_posix(),
            "measureAnalytics": (logical_root / "measure.analytics.json").as_posix(),
        }
    destination.mkdir(parents=True, exist_ok=True)
    payload = deepcopy(result)
    payload["outputs"] = serialized_outputs
    payload["semanticFingerprint"] = semantic_fingerprint(payload)
    validate_paired_experiment_result(payload, schema_path=schema_path)
    _write_json(Path(outputs["baselineAnalytics"]), payload["baseline"]["analytics"])
    _write_json(Path(outputs["measureAnalytics"]), payload["measure"]["analytics"])
    _write_json(Path(outputs["pairResult"]), payload)
    return outputs


def generate_and_write_abay_signal_pair(
    source_analytics_path: str | Path,
    aggregate_demand_path: str | Path,
    output_dir: str | Path,
    *,
    context_network_path: str | Path,
    source_analytics_logical_path: str | None = None,
    aggregate_demand_logical_path: str | None = None,
    logical_output_dir: str | None = None,
    contract_schema_path: str | Path | None = None,
    **model_parameters: Any,
) -> dict[str, str]:
    source_path = Path(source_analytics_path)
    demand_path = Path(aggregate_demand_path)
    network_path = Path(context_network_path)
    source_ref = {
        "relativePath": source_analytics_logical_path or _logical_path(source_path),
        "sha256": _sha256(source_path),
    }
    demand_ref = {
        "relativePath": aggregate_demand_logical_path or _logical_path(demand_path),
        "sha256": _sha256(demand_path),
    }
    result = generate_abay_signal_pair(
        _load_json(source_path),
        _load_json(demand_path),
        source_analytics_ref=source_ref,
        aggregate_demand_ref=demand_ref,
        context_network_fingerprint=_sha256(network_path),
        schema_path=contract_schema_path,
        **model_parameters,
    )
    return write_paired_experiment(
        result,
        output_dir,
        logical_output_dir=logical_output_dir,
        schema_path=contract_schema_path,
    )


def _normalize_source_analytics(source: Mapping[str, Any], *, demand_control: dict[str, Any]) -> dict[str, Any]:
    payload = deepcopy(dict(source))
    for key in (
        "executive_kpis",
        "executiveKpis",
        "pairedExperiment",
        "generatedAt",
        "provenance",
        "outputs",
    ):
        payload.pop(key, None)
    required = {"summary", "node_throughput", "time_series", "ml_forecast"}
    missing = required - payload.keys()
    if missing:
        raise ValueError(f"Source analytics missing required fields: {sorted(missing)}")
    extra = payload.keys() - required
    if extra:
        raise ValueError(f"Source analytics has unsupported fields: {sorted(extra)}")
    summary = payload.get("summary")
    if not isinstance(summary, dict):
        raise ValueError("Source analytics summary must be an object")
    average_trip_time = _finite_positive(
        summary.get("average_trip_time_seconds"), field="summary.average_trip_time_seconds"
    )
    summary_congestion = _bounded_finite(
        summary.get("congestion_index"), field="summary.congestion_index", minimum=0, maximum=100
    )
    _require_source_precision(average_trip_time, decimals=2, field="summary.average_trip_time_seconds")
    _require_source_precision(summary_congestion, decimals=2, field="summary.congestion_index")
    average_trip_time = round(average_trip_time, 2)
    summary_congestion = round(summary_congestion, 2)
    summary = {
        "average_trip_time_seconds": average_trip_time,
        "congestion_index": summary_congestion,
        "total_active_vehicles": demand_control["modeledVehicleCount"],
    }
    time_series = payload.get("time_series")
    if not isinstance(time_series, list) or not time_series:
        raise ValueError("Source analytics time_series must be a non-empty list")
    normalized_series: list[dict[str, Any]] = []
    for index, item in enumerate(time_series):
        if not isinstance(item, dict) or set(item) != {"hour", "congestion_index", "avg_speed_kph"}:
            raise ValueError(f"time_series[{index}] must contain only hour, congestion_index, avg_speed_kph")
        congestion = _bounded_finite(
            item["congestion_index"],
            field=f"time_series[{index}].congestion_index",
            minimum=0,
            maximum=100,
        )
        speed = _bounded_finite(
            item["avg_speed_kph"],
            field=f"time_series[{index}].avg_speed_kph",
            minimum=5,
            maximum=80,
        )
        _require_source_precision(
            congestion, decimals=2, field=f"time_series[{index}].congestion_index"
        )
        _require_source_precision(speed, decimals=1, field=f"time_series[{index}].avg_speed_kph")
        congestion = round(congestion, 2)
        speed = round(speed, 1)
        normalized_series.append(
            {"hour": str(item["hour"]), "congestion_index": congestion, "avg_speed_kph": speed}
        )
    node_throughput = payload.get("node_throughput")
    ml_forecast = payload.get("ml_forecast")
    if not isinstance(node_throughput, list) or not isinstance(ml_forecast, list):
        raise ValueError("node_throughput and ml_forecast must be lists")
    return {
        "summary": summary,
        "node_throughput": deepcopy(node_throughput),
        "time_series": normalized_series,
        "ml_forecast": deepcopy(ml_forecast),
        "demandControl": deepcopy(demand_control),
    }


def _variant_analytics(
    normalized: Mapping[str, Any],
    *,
    delay_s: float,
    trip_time_s: float,
    ratio: float,
    seed: int,
    base_series_fingerprint: str,
    network_context: dict[str, Any],
) -> dict[str, Any]:
    if not math.isfinite(ratio) or ratio <= 0:
        raise ValueError("Trip-time ratio must be finite and greater than zero")
    clamped_fields: list[str] = []
    base_summary = normalized["summary"]
    raw_summary_congestion = float(base_summary["congestion_index"]) * ratio
    summary_congestion = _clamp(raw_summary_congestion, 0, 100)
    if summary_congestion != raw_summary_congestion:
        clamped_fields.append("/summary/congestion_index")
    series: list[dict[str, Any]] = []
    for index, item in enumerate(normalized["time_series"]):
        raw_congestion = float(item["congestion_index"]) * ratio
        congestion = _clamp(raw_congestion, 0, 100)
        if congestion != raw_congestion:
            clamped_fields.append(f"/time_series/{index}/congestion_index")
        raw_speed = float(item["avg_speed_kph"]) / ratio
        speed = _clamp(raw_speed, 5, 80)
        if speed != raw_speed:
            clamped_fields.append(f"/time_series/{index}/avg_speed_kph")
        series.append(
            {
                "hour": item["hour"],
                "congestion_index": round(congestion, 2),
                "avg_speed_kph": round(speed, 1),
            }
        )
    return {
        "summary": {
            "average_trip_time_seconds": round(trip_time_s, 2),
            "congestion_index": round(summary_congestion, 2),
            "total_active_vehicles": normalized["demandControl"]["modeledVehicleCount"],
        },
        "node_throughput": deepcopy(normalized["node_throughput"]),
        "time_series": series,
        "ml_forecast": deepcopy(normalized["ml_forecast"]),
        "demandControl": deepcopy(normalized["demandControl"]),
        "pairedExperiment": {
            "schemaVersion": SCHEMA_VERSION,
            "modelId": MODEL_ID,
            "scenarioId": SCENARIO_ID,
            "signalDelaySeconds": delay_s,
            "seed": seed,
            "baseSeriesFingerprint": base_series_fingerprint,
            "contextNetworkFingerprint": deepcopy(network_context),
            "clampedFields": clamped_fields,
        },
    }


def _build_demand_control(
    aggregate: Mapping[str, Any], *, demand_ref: dict[str, str], seed: int
) -> dict[str, Any]:
    allowed = {
        "schemaVersion",
        "mode",
        "modeledVehicleCount",
        "pattern",
        "sampleTripCount",
        "rawTripsIncluded",
        "originalSnapshot",
        "expansion",
        "claimLevel",
        "limitations",
    }
    extra = set(aggregate) - allowed
    if extra:
        raise ValueError(f"Aggregate demand fixture has unsupported fields: {sorted(extra)}")
    if aggregate.get("mode") != "aggregate-count-v1":
        raise ValueError("Aggregate demand mode must be aggregate-count-v1")
    if aggregate.get("rawTripsIncluded") is not False:
        raise ValueError("Aggregate demand fixture must state rawTripsIncluded=false")
    original_snapshot = aggregate.get("originalSnapshot")
    if not isinstance(original_snapshot, dict) or set(original_snapshot) != {"relativePath", "sha256"}:
        raise ValueError("Aggregate demand originalSnapshot must contain relativePath and sha256 only")
    original_path = Path(str(original_snapshot.get("relativePath", "")))
    if not str(original_snapshot.get("relativePath", "")) or original_path.is_absolute() or ".." in original_path.parts:
        raise ValueError("Aggregate demand originalSnapshot.relativePath must be a safe logical path")
    original_snapshot_sha256 = str(original_snapshot.get("sha256", ""))
    _validate_sha256(original_snapshot_sha256, field="aggregateDemand.originalSnapshot.sha256")
    modeled = aggregate.get("modeledVehicleCount")
    sample = aggregate.get("sampleTripCount")
    expansion = aggregate.get("expansion")
    if isinstance(modeled, bool) or not isinstance(modeled, int) or modeled <= 0:
        raise ValueError("modeledVehicleCount must be a positive integer")
    if isinstance(sample, bool) or not isinstance(sample, int) or sample <= 0:
        raise ValueError("sampleTripCount must be a positive integer")
    if not isinstance(expansion, dict):
        raise ValueError("Aggregate demand expansion must be an object")
    if set(expansion) != {"numerator", "denominator", "rounding"}:
        raise ValueError("Aggregate demand expansion must contain numerator, denominator, and rounding only")
    numerator = expansion.get("numerator")
    denominator = expansion.get("denominator")
    if isinstance(numerator, bool) or not isinstance(numerator, int) or numerator <= 0:
        raise ValueError("Aggregate demand expansion numerator must be a positive integer")
    if isinstance(denominator, bool) or not isinstance(denominator, int) or denominator <= 0:
        raise ValueError("Aggregate demand expansion denominator must be a positive integer")
    if expansion.get("rounding") != "exact-required":
        raise ValueError("Aggregate demand expansion rounding must be exact-required")
    if modeled * denominator != sample * numerator:
        raise ValueError("Aggregate demand must satisfy the exact integer identity; rounding is forbidden")
    pattern = aggregate.get("pattern")
    if not isinstance(pattern, str) or not pattern:
        raise ValueError("Aggregate demand pattern must be a non-empty string")
    return {
        "mode": "aggregate-count-v1",
        "modeledVehicleCount": modeled,
        "seed": seed,
        "pattern": pattern,
        "source": {
            **demand_ref,
            "sampleTripCount": sample,
            "originalSnapshotSha256": original_snapshot_sha256,
            "rawTripsIncluded": False,
        },
        "expansion": {
            "numerator": numerator,
            "denominator": denominator,
            "rounding": "exact-required",
        },
    }


def _source_primitive_vehicle_count(source: Mapping[str, Any]) -> int:
    summary = source.get("summary")
    if not isinstance(summary, Mapping):
        raise ValueError("Source analytics summary must be an object")
    count = summary.get("total_active_vehicles")
    if isinstance(count, bool) or not isinstance(count, int) or count <= 0:
        raise ValueError("summary.total_active_vehicles must be a positive integer")
    return count


def _artifact_ref(value: Mapping[str, str], *, field: str) -> dict[str, str]:
    if set(value) != {"relativePath", "sha256"}:
        raise ValueError(f"{field} must contain relativePath and sha256 only")
    relative_path = str(value["relativePath"])
    path = Path(relative_path)
    if not relative_path or path.is_absolute() or ".." in path.parts:
        raise ValueError(f"{field}.relativePath must be a safe logical relative path")
    digest = str(value["sha256"])
    _validate_sha256(digest, field=f"{field}.sha256")
    return {"relativePath": relative_path, "sha256": digest}


def _validate_number(field: str, value: Any, *, minimum: float, maximum: float) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
        raise ValueError(f"{field} must be a finite number")
    if not minimum <= float(value) <= maximum:
        raise ValueError(f"{field} must be in {minimum}..{maximum}")


def _normalized_contract_number(value: int | float) -> int | float:
    """Use one JSON number representation so equal inputs hash identically."""

    number = float(value)
    return int(number) if number.is_integer() else number


def _require_source_precision(value: float, *, decimals: int, field: str) -> None:
    if not math.isclose(value, round(value, decimals), rel_tol=0.0, abs_tol=1e-12):
        raise ValueError(
            f"{field} must already be serialized to {decimals} decimal places for proxy-v1"
        )


def _finite_positive(value: Any, *, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field} must be a finite positive number")
    number = float(value)
    if not math.isfinite(number) or number <= 0:
        raise ValueError(f"{field} must be a finite positive number")
    return number


def _bounded_finite(value: Any, *, field: str, minimum: float, maximum: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field} must be a finite number")
    number = float(value)
    if not math.isfinite(number) or not minimum <= number <= maximum:
        raise ValueError(f"{field} must be a finite number in {minimum}..{maximum}")
    return number


def _validate_sha256(value: str, *, field: str) -> None:
    if len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
        raise ValueError(f"{field} must be a lowercase SHA-256 hex digest")


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return min(float(maximum), max(float(minimum), float(value)))


def _logical_path(path: Path) -> str:
    if not path.is_absolute():
        return path.as_posix()
    try:
        return path.resolve().relative_to(Path.cwd().resolve()).as_posix()
    except ValueError:
        return path.name


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected a JSON object at {path}")
    return payload


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True, allow_nan=False), encoding="utf-8")
