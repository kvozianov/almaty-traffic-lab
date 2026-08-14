from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import json
import math
import os
from pathlib import Path
from typing import Any, Mapping

from .run_metadata import CLAIM_LABELS


def app_config() -> dict[str, object]:
    return {
        "mapProvider": os.getenv("TRAFFIC_SIM_MAP_PROVIDER", "leaflet"),
        "has2GisKey": bool(os.getenv("2GIS_API_KEY")),
        "twoGisApiKey": os.getenv("2GIS_API_KEY", ""),
        "hasYandexKey": bool(os.getenv("YANDEX_MAPS_API_KEY")),
        "trafficDataProvider": os.getenv("TRAFFIC_DATA_PROVIDER", "synthetic"),
        "defaultTime": os.getenv("TRAFFIC_SIM_DEFAULT_TIME", "17:00"),
        "policy": os.getenv("TRAFFIC_SIM_POLICY", "heuristic"),
    }


@dataclass(frozen=True, slots=True)
class AnalyticsRunConfig:
    role: str
    pattern: str
    closed_streets: str
    path: str


@dataclass(frozen=True, slots=True)
class PairedExperimentConfig:
    model_id: str
    claim_level: str
    source_analytics_path: str
    aggregate_demand_path: str
    context_network_path: str
    output_path: str
    baseline_delay_s: float
    measure_delay_s: float
    affected_signals_per_trip: int
    realization_factor: float


@dataclass(frozen=True, slots=True)
class ReproductionConfig:
    id: str
    version: int
    claim_level: str
    seed: int
    scenario_config: dict[str, Any]
    output_root: str
    trajectory_path: str
    analytics_runs: tuple[AnalyticsRunConfig, ...]
    paired_experiment: PairedExperimentConfig


_TOP_LEVEL_FIELDS = frozenset(
    {
        "id",
        "version",
        "claimLevel",
        "seed",
        "scenario",
        "outputRoot",
        "pairedExperiment",
        "trajectoryExport",
        "analytics",
    }
)
_SCENARIO_FIELDS = frozenset(
    {
        "id",
        "corridor",
        "decisionQuestion",
        "claimLevel",
        "baseline",
        "measure",
        "costs",
        "assumptions",
        "risks",
        "decisionOptions",
    }
)


def load_reproduction_config(path: str | Path = "simulation.config.json") -> ReproductionConfig:
    """Load the closed, versioned reproduction contract from disk."""

    return parse_reproduction_config(_load_json(path))


def parse_reproduction_config(payload: Mapping[str, Any]) -> ReproductionConfig:
    """Parse a reproduction config without silently accepting unknown fields.

    The canonical portfolio release calls this function on the manifest-resolved
    ``reproductionConfig`` source. Keeping parsing independent from a filesystem
    path prevents the generator from escaping the declared source slice.
    """

    root = _closed_object(payload, expected=_TOP_LEVEL_FIELDS, field="simulation config")
    config_id = _non_empty_string(root["id"], field="id")
    version = _integer(root["version"], field="version", minimum=1)
    claim_level = _claim_level(root["claimLevel"], field="claimLevel")
    seed = _integer(root["seed"], field="seed")
    scenario = _scenario(root["scenario"])
    output_root = _safe_relative_path(
        _non_empty_string(root["outputRoot"], field="outputRoot"),
        field="outputRoot",
    )
    pair_claim_level = _claim_level(scenario["claimLevel"], field="scenario.claimLevel")
    paired_experiment = _paired_experiment(
        root["pairedExperiment"],
        claim_level=pair_claim_level,
    )
    trajectory = _closed_object(
        root["trajectoryExport"],
        expected={"format", "path", "source"},
        field="trajectoryExport",
    )
    if trajectory["format"] != "csv":
        raise ValueError("trajectoryExport.format must be csv")
    _non_empty_string(trajectory["source"], field="trajectoryExport.source")
    trajectory_path = _safe_relative_path(
        _non_empty_string(trajectory["path"], field="trajectoryExport.path"),
        field="trajectoryExport.path",
    )
    raw_analytics = root["analytics"]
    if not isinstance(raw_analytics, list):
        raise ValueError("analytics must be an array")
    analytics_runs = tuple(_analytics_run(item, index=index) for index, item in enumerate(raw_analytics))
    roles = [item.role for item in analytics_runs]
    if sorted(roles) != ["baseline", "measure"]:
        raise ValueError("simulation config analytics must contain exactly one baseline and one measure role")

    baseline_scenario = scenario["baseline"]["scenario"]
    measure_scenario = scenario["measure"]["scenario"]
    if baseline_scenario["signal_delay_s"] != paired_experiment.baseline_delay_s:
        raise ValueError(
            "simulation config drift: scenario baseline delay does not match pairedExperiment.baselineDelaySeconds"
        )
    if measure_scenario["signal_delay_s"] != paired_experiment.measure_delay_s:
        raise ValueError(
            "simulation config drift: scenario measure delay does not match pairedExperiment.measureDelaySeconds"
        )
    for role, nested in (("baseline", baseline_scenario), ("measure", measure_scenario)):
        if nested["claim_level"] != pair_claim_level:
            raise ValueError(
                f"simulation config drift: scenario {role} claim_level does not match scenario.claimLevel"
            )

    return ReproductionConfig(
        id=config_id,
        version=version,
        claim_level=claim_level,
        seed=seed,
        scenario_config=deepcopy(scenario),
        output_root=output_root,
        trajectory_path=trajectory_path,
        analytics_runs=analytics_runs,
        paired_experiment=paired_experiment,
    )


def _scenario(payload: Any) -> dict[str, Any]:
    scenario = _closed_object(payload, expected=_SCENARIO_FIELDS, field="scenario")
    _non_empty_string(scenario["id"], field="scenario.id")
    _non_empty_string(scenario["decisionQuestion"], field="scenario.decisionQuestion")
    _claim_level(scenario["claimLevel"], field="scenario.claimLevel")

    corridor = _closed_object(
        scenario["corridor"],
        expected={"id", "name", "anchor"},
        field="scenario.corridor",
    )
    for key in ("id", "name", "anchor"):
        _non_empty_string(corridor[key], field=f"scenario.corridor.{key}")

    baseline = _variant_scenario(scenario["baseline"], role="baseline")
    measure = _variant_scenario(scenario["measure"], role="measure")

    costs = _closed_object(
        scenario["costs"],
        expected={
            "capexKzt",
            "opexKztPerYear",
            "capexPlaceholder",
            "opexPlaceholder",
            "roiPaybackPlaceholder",
            "claimLevel",
            "notes",
        },
        field="scenario.costs",
    )
    _non_negative_number(costs["capexKzt"], field="scenario.costs.capexKzt")
    _non_negative_number(costs["opexKztPerYear"], field="scenario.costs.opexKztPerYear")
    for key in ("capexPlaceholder", "opexPlaceholder", "roiPaybackPlaceholder"):
        if not isinstance(costs[key], bool):
            raise ValueError(f"scenario.costs.{key} must be a boolean")
    _claim_level(costs["claimLevel"], field="scenario.costs.claimLevel")
    _non_empty_string(costs["notes"], field="scenario.costs.notes")

    assumptions = _string_array(scenario["assumptions"], field="scenario.assumptions")
    risks = _string_array(scenario["risks"], field="scenario.risks")
    decisions = _string_array(scenario["decisionOptions"], field="scenario.decisionOptions")
    if len(set(decisions)) != len(decisions):
        raise ValueError("scenario.decisionOptions must not contain duplicates")

    return {
        "id": scenario["id"],
        "corridor": dict(corridor),
        "decisionQuestion": scenario["decisionQuestion"],
        "claimLevel": scenario["claimLevel"],
        "baseline": baseline,
        "measure": measure,
        "costs": dict(costs),
        "assumptions": assumptions,
        "risks": risks,
        "decisionOptions": decisions,
    }


def _variant_scenario(payload: Any, *, role: str) -> dict[str, Any]:
    expected = {"label", "analyticsPath", "scenario"}
    if role == "measure":
        expected |= {"type", "description"}
    variant = _closed_object(payload, expected=expected, field=f"scenario.{role}")
    _non_empty_string(variant["label"], field=f"scenario.{role}.label")
    analytics_path = _safe_relative_path(
        _non_empty_string(variant["analyticsPath"], field=f"scenario.{role}.analyticsPath"),
        field=f"scenario.{role}.analyticsPath",
    )
    nested = _closed_object(
        variant["scenario"],
        expected={"pattern", "signal_delay_s", "claim_level"},
        field=f"scenario.{role}.scenario",
    )
    _non_empty_string(nested["pattern"], field=f"scenario.{role}.scenario.pattern")
    delay = _bounded_number(
        nested["signal_delay_s"],
        field=f"scenario.{role}.scenario.signal_delay_s",
        minimum=0,
        maximum=120,
    )
    nested_claim = _claim_level(
        nested["claim_level"],
        field=f"scenario.{role}.scenario.claim_level",
    )
    result: dict[str, Any] = {
        "label": variant["label"],
        "analyticsPath": analytics_path,
        "scenario": {
            "pattern": nested["pattern"],
            "signal_delay_s": delay,
            "claim_level": nested_claim,
        },
    }
    if role == "measure":
        result["type"] = _non_empty_string(variant["type"], field="scenario.measure.type")
        result["description"] = _non_empty_string(
            variant["description"], field="scenario.measure.description"
        )
    return result


def _analytics_run(payload: Any, *, index: int) -> AnalyticsRunConfig:
    field = f"analytics[{index}]"
    item = _closed_object_with_optional(
        payload,
        required={"role", "pattern", "path"},
        optional={"closedStreets"},
        field=field,
    )
    role = _non_empty_string(item["role"], field=f"{field}.role")
    if role not in {"baseline", "measure"}:
        raise ValueError(f"{field}.role must be baseline or measure")
    return AnalyticsRunConfig(
        role=role,
        pattern=_non_empty_string(item["pattern"], field=f"{field}.pattern"),
        closed_streets=_string(item.get("closedStreets", ""), field=f"{field}.closedStreets"),
        path=_safe_relative_path(
            _non_empty_string(item["path"], field=f"{field}.path"),
            field=f"{field}.path",
        ),
    )


def _paired_experiment(payload: Any, *, claim_level: str) -> PairedExperimentConfig:
    pair = _closed_object(
        payload,
        expected={
            "modelId",
            "sourceAnalyticsPath",
            "aggregateDemandPath",
            "contextNetworkPath",
            "outputPath",
            "baselineDelaySeconds",
            "measureDelaySeconds",
            "affectedSignalsPerTrip",
            "realizationFactor",
        },
        field="pairedExperiment",
    )
    if pair["modelId"] != "abay-signal-delay-proxy-v1":
        raise ValueError("pairedExperiment.modelId must be abay-signal-delay-proxy-v1")
    if claim_level != "proxy":
        raise ValueError("pairedExperiment claim derived from scenario.claimLevel must be proxy")
    baseline_delay = _bounded_number(
        pair["baselineDelaySeconds"],
        field="pairedExperiment.baselineDelaySeconds",
        minimum=0,
        maximum=120,
    )
    measure_delay = _bounded_number(
        pair["measureDelaySeconds"],
        field="pairedExperiment.measureDelaySeconds",
        minimum=0,
        maximum=120,
    )
    affected = _integer(
        pair["affectedSignalsPerTrip"],
        field="pairedExperiment.affectedSignalsPerTrip",
        minimum=1,
        maximum=20,
    )
    realization = _bounded_number(
        pair["realizationFactor"],
        field="pairedExperiment.realizationFactor",
        minimum=0,
        maximum=1,
    )
    return PairedExperimentConfig(
        model_id="abay-signal-delay-proxy-v1",
        claim_level=claim_level,
        source_analytics_path=_safe_relative_path(
            _non_empty_string(pair["sourceAnalyticsPath"], field="pairedExperiment.sourceAnalyticsPath"),
            field="pairedExperiment.sourceAnalyticsPath",
        ),
        aggregate_demand_path=_safe_relative_path(
            _non_empty_string(pair["aggregateDemandPath"], field="pairedExperiment.aggregateDemandPath"),
            field="pairedExperiment.aggregateDemandPath",
        ),
        context_network_path=_safe_relative_path(
            _non_empty_string(pair["contextNetworkPath"], field="pairedExperiment.contextNetworkPath"),
            field="pairedExperiment.contextNetworkPath",
        ),
        output_path=_safe_relative_path(
            _non_empty_string(pair["outputPath"], field="pairedExperiment.outputPath"),
            field="pairedExperiment.outputPath",
        ),
        baseline_delay_s=baseline_delay,
        measure_delay_s=measure_delay,
        affected_signals_per_trip=affected,
        realization_factor=realization,
    )


def _closed_object(payload: Any, *, expected: set[str] | frozenset[str], field: str) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        raise ValueError(f"{field} must be an object")
    keys = set(payload)
    missing = sorted(set(expected) - keys)
    unknown = sorted(keys - set(expected))
    if missing or unknown:
        raise ValueError(f"{field} has invalid fields: missing={missing}, unknown={unknown}")
    return dict(payload)


def _closed_object_with_optional(
    payload: Any,
    *,
    required: set[str] | frozenset[str],
    optional: set[str] | frozenset[str],
    field: str,
) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        raise ValueError(f"{field} must be an object")
    keys = set(payload)
    missing = sorted(set(required) - keys)
    unknown = sorted(keys - set(required) - set(optional))
    if missing or unknown:
        raise ValueError(f"{field} has invalid fields: missing={missing}, unknown={unknown}")
    return dict(payload)


def _load_json(path: str | Path) -> dict[str, Any]:
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"Cannot load simulation config {path}: {error}") from error
    if not isinstance(payload, dict):
        raise ValueError("simulation config must contain an object")
    return payload


def _safe_relative_path(value: str, *, field: str) -> str:
    path = Path(value)
    if not value or path.is_absolute() or ".." in path.parts or ".staging" in path.parts:
        raise ValueError(f"{field} must be a relative path without '..' or '.staging' segments")
    return path.as_posix()


def _bounded_number(value: Any, *, field: str, minimum: float, maximum: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field} must be a finite number in {minimum}..{maximum}")
    number = float(value)
    if not math.isfinite(number) or not minimum <= number <= maximum:
        raise ValueError(f"{field} must be a finite number in {minimum}..{maximum}")
    return number


def _non_negative_number(value: Any, *, field: str) -> float:
    return _bounded_number(value, field=field, minimum=0, maximum=float("inf"))


def _integer(value: Any, *, field: str, minimum: int | None = None, maximum: int | None = None) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{field} must be an integer")
    if minimum is not None and value < minimum:
        raise ValueError(f"{field} must be at least {minimum}")
    if maximum is not None and value > maximum:
        raise ValueError(f"{field} must be at most {maximum}")
    return value


def _string(value: Any, *, field: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a string")
    return value


def _non_empty_string(value: Any, *, field: str) -> str:
    text = _string(value, field=field)
    if not text.strip() or text != text.strip():
        raise ValueError(f"{field} must be a non-empty trimmed string")
    return text


def _string_array(value: Any, *, field: str) -> list[str]:
    if not isinstance(value, list) or not value:
        raise ValueError(f"{field} must be a non-empty array")
    return [_non_empty_string(item, field=f"{field}[{index}]") for index, item in enumerate(value)]


def _claim_level(value: Any, *, field: str) -> str:
    claim = _non_empty_string(value, field=field)
    if claim not in CLAIM_LABELS:
        raise ValueError(f"Unsupported {field}: {claim}")
    return claim
