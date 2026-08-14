from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any

from .contracts import canonical_json, validate_claim_level


@dataclass(frozen=True, slots=True)
class ExecutiveKpiAssumptions:
    average_vehicle_occupancy: float = 1.0
    value_of_time_kzt_per_hour: float = 2500.0
    annualization_days: int = 250
    peak_hours_per_day: float = 2.0
    co2_kg_per_vehicle_hour: float = 2.4
    nox_kg_per_vehicle_hour: float = 0.006
    default_capex_kzt: float = 350_000_000.0
    default_opex_kzt_per_year: float = 25_000_000.0


def build_executive_kpi_block(
    baseline: dict[str, Any],
    measure: dict[str, Any],
    *,
    assumptions: ExecutiveKpiAssumptions | None = None,
    capex_kzt: float | None = None,
    opex_kzt_per_year: float | None = None,
    capex_placeholder: bool = True,
    opex_placeholder: bool = True,
    roi_payback_placeholder: bool = True,
    claim_level: str = "proxy",
) -> dict[str, Any]:
    assumptions = assumptions or ExecutiveKpiAssumptions()
    validate_claim_level(claim_level)
    for field, value in (
        ("capex_placeholder", capex_placeholder),
        ("opex_placeholder", opex_placeholder),
        ("roi_payback_placeholder", roi_payback_placeholder),
    ):
        if not isinstance(value, bool):
            raise ValueError(f"{field} must be a boolean")
    baseline_summary = _summary(baseline)
    measure_summary = _summary(measure)
    vehicles, demand_comparability = _vehicle_count_and_comparability(baseline, measure)
    trip_validator = (
        _required_positive
        if demand_comparability["mode"] == "controlled-aggregate-count-v1"
        else _required_non_negative
    )
    baseline_trip_s = trip_validator(
        _first(baseline_summary, "average_trip_time_seconds", "averageTripTimeSeconds"),
        field="baseline average trip time",
    )
    measure_trip_s = trip_validator(
        _first(measure_summary, "average_trip_time_seconds", "averageTripTimeSeconds"),
        field="measure average trip time",
    )
    if demand_comparability["mode"] == "controlled-aggregate-count-v1":
        baseline_congestion = _required_bounded(
            _first(baseline_summary, "congestion_index", "congestionIndex"),
            field="baseline congestion index",
            minimum=0,
            maximum=100,
        )
        measure_congestion = _required_bounded(
            _first(measure_summary, "congestion_index", "congestionIndex"),
            field="measure congestion index",
            minimum=0,
            maximum=100,
        )
    else:
        baseline_congestion = _finite(
            _first(baseline_summary, "congestion_index", "congestionIndex"),
            field="baseline congestion index",
        )
        measure_congestion = _finite(
            _first(measure_summary, "congestion_index", "congestionIndex"),
            field="measure congestion index",
        )
    baseline_speed = _average_speed(baseline)
    measure_speed = _average_speed(measure)
    average_vehicle_occupancy = _required_positive(
        assumptions.average_vehicle_occupancy,
        field="average_vehicle_occupancy",
    )
    baseline_person_hours = baseline_trip_s * vehicles * average_vehicle_occupancy / 3600.0
    measure_person_hours = measure_trip_s * vehicles * average_vehicle_occupancy / 3600.0
    person_hours_saved = baseline_person_hours - measure_person_hours
    baseline_queue = baseline_congestion / 100.0
    measure_queue = measure_congestion / 100.0
    baseline_bus_reliability = _bus_reliability(baseline_congestion, baseline_speed)
    measure_bus_reliability = _bus_reliability(measure_congestion, measure_speed)
    baseline_co2 = _emissions_kg(baseline_trip_s, vehicles, assumptions.co2_kg_per_vehicle_hour)
    measure_co2 = _emissions_kg(measure_trip_s, vehicles, assumptions.co2_kg_per_vehicle_hour)
    baseline_nox = _emissions_kg(baseline_trip_s, vehicles, assumptions.nox_kg_per_vehicle_hour)
    measure_nox = _emissions_kg(measure_trip_s, vehicles, assumptions.nox_kg_per_vehicle_hour)
    capex = _non_negative(
        assumptions.default_capex_kzt if capex_kzt is None else capex_kzt,
        field="capex_kzt",
    )
    opex = _non_negative(
        assumptions.default_opex_kzt_per_year if opex_kzt_per_year is None else opex_kzt_per_year,
        field="opex_kzt_per_year",
    )
    annual_time_savings_kzt = (
        max(person_hours_saved, 0.0)
        * assumptions.value_of_time_kzt_per_hour
        * assumptions.peak_hours_per_day
        * assumptions.annualization_days
    )
    net_annual_benefit = annual_time_savings_kzt - opex
    payback_years = capex / net_annual_benefit if net_annual_benefit > 0 else None
    roi_ratio = net_annual_benefit / capex if capex > 0 else None
    clamp_reasons = _kpi_clamp_reasons(baseline, measure)
    bus_clamps = []
    if _bus_reliability_raw(baseline_congestion, baseline_speed) != baseline_bus_reliability:
        bus_clamps.append("baseline:bus_reliability_proxy")
    if _bus_reliability_raw(measure_congestion, measure_speed) != measure_bus_reliability:
        bus_clamps.append("measure:bus_reliability_proxy")
    if bus_clamps:
        existing = clamp_reasons.get("bus_reliability_proxy")
        reason = "Bus reliability formula clamp active at " + ", ".join(bus_clamps)
        clamp_reasons["bus_reliability_proxy"] = f"{existing}; {reason}" if existing else reason

    return {
        "claimLevel": claim_level,
        "demandComparability": demand_comparability,
        "confidence": {
            "level": "low-medium",
            "score": 0.42,
            "claimLevel": claim_level,
            "notes": "Fixed heuristic proxy-readiness marker, not a statistical confidence estimate; observed traffic, cost, and calibration evidence are still required.",
        },
        "assumptions": {
            "averageVehicleOccupancy": average_vehicle_occupancy,
            "averageVehicleOccupancyClaimLevel": "proxy",
            "valueOfTimeKztPerHour": assumptions.value_of_time_kzt_per_hour,
            "annualizationDays": assumptions.annualization_days,
            "peakHoursPerDay": assumptions.peak_hours_per_day,
            "co2KgPerVehicleHour": assumptions.co2_kg_per_vehicle_hour,
            "noxKgPerVehicleHour": assumptions.nox_kg_per_vehicle_hour,
        },
        "kpis": [
            _kpi(
                "person_hours",
                "Person-hours per modeled peak window",
                "person-hours",
                baseline_person_hours,
                measure_person_hours,
                "lower_is_better",
                claim_level,
                "average_trip_time_seconds * modeled_vehicle_count * average_vehicle_occupancy / 3600",
                clamp_reason=clamp_reasons.get("person_hours"),
            ),
            _kpi(
                "person_hours_saved",
                "Person-hours saved",
                "person-hours",
                0.0,
                person_hours_saved,
                "higher_is_better",
                claim_level,
                "baseline_person_hours - measure_person_hours",
            ),
            _kpi(
                "corridor_speed_delta",
                "Average corridor speed delta",
                "km/h",
                baseline_speed,
                measure_speed,
                "higher_is_better",
                claim_level,
                "average(measure.time_series.avg_speed_kph) - average(baseline.time_series.avg_speed_kph)",
                clamp_reason=clamp_reasons.get("corridor_speed_delta"),
            ),
            _kpi(
                "queue_load_proxy",
                "Queue/load proxy",
                "0-1 load",
                baseline_queue,
                measure_queue,
                "lower_is_better",
                claim_level,
                "congestion_index / 100",
                clamp_reason=clamp_reasons.get("queue_load_proxy"),
            ),
            _kpi(
                "bus_reliability_proxy",
                "Bus reliability proxy",
                "%",
                baseline_bus_reliability,
                measure_bus_reliability,
                "higher_is_better",
                claim_level,
                "clamp(95 - congestion_index * 0.45 + average_speed_kph * 0.08, 35, 98)",
                clamp_reason=clamp_reasons.get("bus_reliability_proxy"),
            ),
            _kpi(
                "co2_proxy",
                "CO2 proxy",
                "kg",
                baseline_co2,
                measure_co2,
                "lower_is_better",
                claim_level,
                "vehicle_hours * 2.4 kg CO2 per vehicle-hour",
                clamp_reason=clamp_reasons.get("co2_proxy"),
            ),
            _kpi(
                "nox_proxy",
                "NOx proxy",
                "kg",
                baseline_nox,
                measure_nox,
                "lower_is_better",
                claim_level,
                "vehicle_hours * 0.006 kg NOx per vehicle-hour",
                clamp_reason=clamp_reasons.get("nox_proxy"),
            ),
            _kpi(
                "capex_placeholder",
                "CAPEX placeholder",
                "KZT",
                0.0,
                capex,
                "lower_is_better",
                claim_level,
                "placeholder until engineering estimate is supplied",
                placeholder=capex_placeholder,
            ),
            _kpi(
                "opex_placeholder",
                "OPEX placeholder",
                "KZT/year",
                0.0,
                opex,
                "lower_is_better",
                claim_level,
                "placeholder until operating estimate is supplied",
                placeholder=opex_placeholder,
            ),
            _kpi(
                "annual_time_savings_proxy",
                "Annual time savings proxy",
                "KZT/year",
                0.0,
                annual_time_savings_kzt,
                "higher_is_better",
                claim_level,
                "max((baseline_trip_time_seconds - measure_trip_time_seconds) * modeled_vehicle_count * average_vehicle_occupancy / 3600, 0) * value_of_time * peak_hours_per_day * annualization_days",
            ),
            _kpi(
                "roi_proxy",
                "ROI proxy",
                "ratio",
                0.0,
                roi_ratio if roi_ratio is not None else 0.0,
                "higher_is_better",
                claim_level,
                "(annual_time_savings_proxy - annual_opex) / capex",
                placeholder=roi_payback_placeholder,
            ),
            _kpi(
                "payback_proxy",
                "Payback proxy",
                "years",
                0.0,
                payback_years if payback_years is not None else 0.0,
                "lower_is_better",
                claim_level,
                "capex / (annual_time_savings_proxy - annual_opex)",
                placeholder=roi_payback_placeholder,
                available=payback_years is not None,
            ),
        ],
    }


def kpis_by_id(block: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(item.get("id")): item for item in block.get("kpis", [])}


def _summary(payload: dict[str, Any]) -> dict[str, Any]:
    summary = payload.get("summary")
    return summary if isinstance(summary, dict) else payload


def _average_speed(payload: dict[str, Any]) -> float:
    series = payload.get("time_series") or payload.get("timeSeries") or []
    speeds = [_num(item.get("avg_speed_kph") or item.get("avgSpeedKph")) for item in series if isinstance(item, dict)]
    speeds = [speed for speed in speeds if speed > 0]
    if speeds:
        return sum(speeds) / len(speeds)
    summary = _summary(payload)
    congestion = _num(summary.get("congestion_index") or summary.get("congestionIndex"))
    return max(8.0, 60.0 - congestion / 2.0)


def _bus_reliability(congestion_index: float, speed_kph: float) -> float:
    return min(98.0, max(35.0, _bus_reliability_raw(congestion_index, speed_kph)))


def _bus_reliability_raw(congestion_index: float, speed_kph: float) -> float:
    return 95.0 - congestion_index * 0.45 + speed_kph * 0.08


def _emissions_kg(trip_time_s: float, vehicles: float, kg_per_vehicle_hour: float) -> float:
    return trip_time_s * vehicles / 3600.0 * kg_per_vehicle_hour


def _kpi(
    kpi_id: str,
    label: str,
    unit: str,
    baseline: float,
    measure: float,
    direction: str,
    claim_level: str,
    formula: str,
    *,
    placeholder: bool = False,
    available: bool = True,
    clamp_reason: str | None = None,
) -> dict[str, Any]:
    return {
        "id": kpi_id,
        "label": label,
        "unit": unit,
        "baseline": _round(baseline),
        "measure": _round(measure),
        "delta": _round(measure - baseline),
        "direction": direction,
        "claimLevel": claim_level,
        "formula": formula,
        "placeholder": placeholder,
        "available": available,
        "clampAffected": clamp_reason is not None,
        "clampReason": clamp_reason,
    }


def _num(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _round(value: float) -> float:
    return round(value, 3)


def _first(payload: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in payload:
            return payload[key]
    return None


def _required_positive(value: Any, *, field: str) -> float:
    number = _finite(value, field=field)
    if number <= 0:
        raise ValueError(f"{field} must be greater than zero")
    return number


def _required_non_negative(value: Any, *, field: str) -> float:
    number = _finite(value, field=field)
    if number < 0:
        raise ValueError(f"{field} must be non-negative")
    return number


def _required_bounded(value: Any, *, field: str, minimum: float, maximum: float) -> float:
    number = _finite(value, field=field)
    if not minimum <= number <= maximum:
        raise ValueError(f"{field} must be in {minimum}..{maximum}")
    return number


def _non_negative(value: Any, *, field: str) -> float:
    number = _finite(value, field=field)
    if number < 0:
        raise ValueError(f"{field} must be non-negative")
    return number


def _finite(value: Any, *, field: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{field} must be a finite number")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be a finite number") from exc
    if not math.isfinite(number):
        raise ValueError(f"{field} must be a finite number")
    return number


def _vehicle_count_and_comparability(
    baseline: dict[str, Any], measure: dict[str, Any]
) -> tuple[float, dict[str, Any]]:
    baseline_demand = baseline.get("demandControl")
    measure_demand = measure.get("demandControl")
    baseline_summary = _summary(baseline)
    measure_summary = _summary(measure)
    baseline_count = _required_positive(
        _first(baseline_summary, "total_active_vehicles", "totalActiveVehicles"),
        field="baseline modeled vehicle count",
    )
    measure_count = _required_positive(
        _first(measure_summary, "total_active_vehicles", "totalActiveVehicles"),
        field="measure modeled vehicle count",
    )
    if baseline_demand is not None or measure_demand is not None:
        if not isinstance(baseline_demand, dict) or not isinstance(measure_demand, dict):
            raise ValueError("Both analytics payloads must include demandControl")
        if canonical_json(baseline_demand) != canonical_json(measure_demand):
            raise ValueError("Baseline and measure demandControl must be canonical deep-equal")
        modeled = _required_positive(baseline_demand.get("modeledVehicleCount"), field="demandControl modeledVehicleCount")
        if baseline_count != modeled or measure_count != modeled:
            raise ValueError("Analytics vehicle counts must equal demandControl modeledVehicleCount")
        return modeled, {
            "comparable": True,
            "mode": "controlled-aggregate-count-v1",
            "modeledVehicleCount": int(modeled),
            "demandControl": baseline_demand,
        }
    # Legacy generators predate demandControl. Preserve their callable contract,
    # but label the result as uncontrolled rather than treating it as paired evidence.
    vehicles = max(baseline_count, measure_count)
    return vehicles, {
        "comparable": baseline_count == measure_count,
        "mode": "legacy-uncontrolled",
        "modeledVehicleCount": int(vehicles) if vehicles.is_integer() else vehicles,
        "baselineVehicleCount": baseline_count,
        "measureVehicleCount": measure_count,
    }


def _kpi_clamp_reasons(baseline: dict[str, Any], measure: dict[str, Any]) -> dict[str, str]:
    paths: list[str] = []
    for role, payload in (("baseline", baseline), ("measure", measure)):
        metadata = payload.get("pairedExperiment")
        if not isinstance(metadata, dict):
            continue
        clamped = metadata.get("clampedFields", [])
        if isinstance(clamped, list):
            paths.extend(f"{role}:{path}" for path in clamped if isinstance(path, str))
    if not paths:
        return {}
    congestion = [path for path in paths if path.endswith("/summary/congestion_index")]
    speed = [path for path in paths if path.endswith("/avg_speed_kph")]
    reasons: dict[str, str] = {}
    if congestion:
        reason = "Proxy congestion clamp active at " + ", ".join(congestion)
        reasons["queue_load_proxy"] = reason
        reasons["bus_reliability_proxy"] = reason
    if speed:
        reason = "Proxy speed clamp active at " + ", ".join(speed)
        reasons["corridor_speed_delta"] = reason
        reasons["bus_reliability_proxy"] = (
            reasons.get("bus_reliability_proxy", "") + ("; " if reasons.get("bus_reliability_proxy") else "") + reason
        )
    return reasons
