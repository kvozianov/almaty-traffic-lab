from __future__ import annotations

from datetime import datetime, timezone
import csv
import html
import json
from pathlib import Path
from pathlib import PurePosixPath
from typing import Any, Mapping


DEFAULT_DOSSIER_PATH = Path("reports/dossiers/abay-signal-retiming/dossier.json")
DEFAULT_PORTFOLIO_MATRIX_PATH = Path("reports/portfolio/month1/kpi_matrix.csv")
DEFAULT_RESEARCH_DIR = Path("reports/research_metrics/abay-signal-retiming")

INPUT_ROLES = ("dossierJson", "portfolioMatrix", "baselineAnalytics", "measureAnalytics")
OUTPUT_ROLES = ("researchJson", "researchAppendix", "researchVisual")


def generate_research_metrics_pack(
    *,
    dossier_path: str | Path = DEFAULT_DOSSIER_PATH,
    portfolio_matrix_path: str | Path = DEFAULT_PORTFOLIO_MATRIX_PATH,
    out_dir: str | Path = DEFAULT_RESEARCH_DIR,
    dossier: dict[str, Any] | None = None,
    input_paths: Mapping[str, str | Path] | None = None,
    artifact_refs: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    physical_inputs, refs = _resolve_generation_context(
        dossier_path=Path(dossier_path),
        portfolio_matrix_path=Path(portfolio_matrix_path),
        dossier=dossier,
        input_paths=input_paths,
        artifact_refs=artifact_refs,
        out_dir=Path(out_dir),
    )
    dossier = dossier or _load_json(physical_inputs["dossierJson"])
    output_dir = Path(out_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    pack = build_research_metrics_pack(
        dossier,
        portfolio_matrix_path=physical_inputs["portfolioMatrix"],
        portfolio_matrix_ref=refs["portfolioMatrix"],
        analytics_paths={
            "baselineAnalytics": physical_inputs["baselineAnalytics"],
            "measureAnalytics": physical_inputs["measureAnalytics"],
        },
    )
    physical_outputs = {
        "researchJson": output_dir / "research_metrics.json",
        "researchAppendix": output_dir / "dossier_appendix.md",
        "researchVisual": output_dir / "research_visual.html",
    }
    pack["inputs"] = {role: refs[role] for role in INPUT_ROLES}
    pack["outputs"] = {
        "json": refs["researchJson"],
        "markdownAppendix": refs["researchAppendix"],
        "htmlVisual": refs["researchVisual"],
    }
    physical_outputs["researchJson"].write_text(
        json.dumps(pack, indent=2, ensure_ascii=True),
        encoding="utf-8",
    )
    _write_markdown_appendix(physical_outputs["researchAppendix"], pack)
    _write_html_visual(physical_outputs["researchVisual"], pack)
    return pack


def build_research_metrics_pack(
    dossier: dict[str, Any],
    *,
    portfolio_matrix_path: str | Path = DEFAULT_PORTFOLIO_MATRIX_PATH,
    portfolio_matrix_ref: str | None = None,
    analytics_paths: Mapping[str, str | Path] | None = None,
) -> dict[str, Any]:
    kpis = {str(item.get("id")): item for item in dossier.get("executiveKpis", {}).get("kpis", []) if isinstance(item, dict)}
    heatmap = _heatmap_from_dossier(dossier, analytics_paths=analytics_paths)
    scenario_matrix = _scenario_matrix_summary(
        portfolio_matrix_path,
        matrix_ref=portfolio_matrix_ref,
    )
    metrics = [
        _reliability_index(kpis),
        _emissions_proxy(kpis),
        _sensitivity_interval(kpis),
        scenario_matrix,
        _network_heatmap_metric(heatmap),
    ]
    return {
        "id": f"{dossier.get('id', 'scenario')}-research-metrics",
        "kind": "research-metrics-pack",
        "claimLevel": "proxy",
        "createdAt": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "scenarioId": dossier.get("id"),
        "runPassportId": dossier.get("trustMetadata", {}).get("runId"),
        "officialFacingReason": "Adds reproducible technical appendix metrics without changing the buyer recommendation.",
        "metrics": metrics,
        "visualization": {
            "id": "network_hour_heatmap",
            "type": "html-svg",
            "claimLevel": "proxy",
            "data": heatmap,
            "formula": "hourly congestion_index values from baseline and measure analytics, rendered as comparable bar intensities",
        },
        "limitations": [
            "Research metrics are technical appendix proxies and should not override the executive dossier decision.",
            "Confidence intervals are deterministic sensitivity bands, not Monte Carlo validation.",
            "Heatmap is generated from existing analytics time series, not observed detector data.",
        ],
    }


def _reliability_index(kpis: dict[str, dict[str, Any]]) -> dict[str, Any]:
    bus = float(kpis.get("bus_reliability_proxy", {}).get("measure", 0.0) or 0.0)
    queue_delta = max(0.0, float(kpis.get("queue_load_proxy", {}).get("delta", 0.0) or 0.0))
    value = max(0.0, min(100.0, bus - queue_delta * 10.0))
    return {
        "id": "reliability_index",
        "label": "Reliability index",
        "unit": "score 0-100",
        "value": round(value, 3),
        "formula": "bus_reliability_proxy.measure - max(queue_load_proxy.delta, 0) * 10",
        "claimLevel": "proxy",
        "officialFacingReason": "Shows whether a measure improves predictable corridor/public transport operation.",
    }


def _emissions_proxy(kpis: dict[str, dict[str, Any]]) -> dict[str, Any]:
    co2_delta = float(kpis.get("co2_proxy", {}).get("delta", 0.0) or 0.0)
    nox_delta = float(kpis.get("nox_proxy", {}).get("delta", 0.0) or 0.0)
    return {
        "id": "emissions_proxy",
        "label": "COPERT-lite emissions proxy delta",
        "unit": "kg per modeled peak window",
        "value": {"co2DeltaKg": round(co2_delta, 3), "noxDeltaKg": round(nox_delta, 3)},
        "formula": "executive CO2/NOx vehicle-hour proxies from G004",
        "claimLevel": "proxy",
        "officialFacingReason": "Provides an environmental appendix metric while sourced emissions data is unavailable.",
    }


def _sensitivity_interval(kpis: dict[str, dict[str, Any]]) -> dict[str, Any]:
    saved = float(kpis.get("person_hours_saved", {}).get("measure", 0.0) or 0.0)
    return {
        "id": "person_hours_sensitivity_interval",
        "label": "Person-hours saved sensitivity band",
        "unit": "person-hours",
        "value": {
            "lower": round(saved * 0.85, 3),
            "center": round(saved, 3),
            "upper": round(saved * 1.15, 3),
        },
        "formula": "person_hours_saved.measure * [0.85, 1.0, 1.15]",
        "claimLevel": "proxy",
        "officialFacingReason": "Makes uncertainty visible before observed validation and Monte Carlo runs exist.",
    }


def _scenario_matrix_summary(
    path: str | Path,
    *,
    matrix_ref: str | None = None,
) -> dict[str, Any]:
    matrix_path = Path(path)
    rows: list[dict[str, str]] = []
    if matrix_path.exists():
        with matrix_path.open(encoding="utf-8", newline="") as file:
            rows = list(csv.DictReader(file))
    best = max(rows, key=lambda row: _float(row.get("person_hours_saved")), default={})
    return {
        "id": "scenario_kpi_matrix",
        "label": "Scenario KPI matrix summary",
        "unit": "scenario rows",
        "value": {
            "scenarioCount": len(rows),
            "bestByPersonHoursSaved": best.get("scenario_id") or best.get("id"),
            "matrixPath": matrix_ref if matrix_ref is not None else str(matrix_path),
        },
        "formula": "max(portfolio matrix person_hours_saved) across scenario rows",
        "claimLevel": "proxy",
        "officialFacingReason": "Lets officials compare the dossier scenario against alternatives without rerunning the dashboard.",
    }


def _network_heatmap_metric(heatmap: list[dict[str, Any]]) -> dict[str, Any]:
    peak = max(heatmap, key=lambda item: item["measureCongestion"], default={})
    return {
        "id": "network_hour_heatmap",
        "label": "Network-hour congestion heatmap",
        "unit": "hourly congestion index",
        "value": {
            "hourCount": len(heatmap),
            "peakMeasureHour": peak.get("hour"),
            "peakMeasureCongestion": peak.get("measureCongestion"),
        },
        "formula": "hourly measure congestion_index values from dossier measure analytics",
        "claimLevel": "proxy",
        "officialFacingReason": "Gives a publication-ready visual showing when the corridor intervention matters most.",
    }


def _heatmap_from_dossier(
    dossier: dict[str, Any],
    *,
    analytics_paths: Mapping[str, str | Path] | None = None,
) -> list[dict[str, Any]]:
    if analytics_paths is None:
        baseline_path = dossier["baseline"]["analyticsPath"]
        measure_path = dossier["proposedMeasure"]["analyticsPath"]
    else:
        _require_exact_roles(analytics_paths, {"baselineAnalytics", "measureAnalytics"}, map_name="analytics_paths")
        baseline_path = analytics_paths["baselineAnalytics"]
        measure_path = analytics_paths["measureAnalytics"]
    baseline = _load_json(baseline_path)
    measure = _load_json(measure_path)
    baseline_by_hour = {
        str(item.get("hour")): float(item.get("congestion_index", 0.0) or 0.0)
        for item in baseline.get("time_series", [])
        if isinstance(item, dict)
    }
    rows = []
    for item in measure.get("time_series", []):
        if not isinstance(item, dict):
            continue
        hour = str(item.get("hour"))
        measure_value = float(item.get("congestion_index", 0.0) or 0.0)
        baseline_value = baseline_by_hour.get(hour, 0.0)
        rows.append(
            {
                "hour": hour,
                "baselineCongestion": round(baseline_value, 3),
                "measureCongestion": round(measure_value, 3),
                "delta": round(measure_value - baseline_value, 3),
            }
        )
    return rows


def _write_markdown_appendix(path: Path, pack: dict[str, Any]) -> None:
    rows = "\n".join(
        f"| `{metric['id']}` | {metric['label']} | `{metric['claimLevel']}` | {metric['formula']} | {metric['officialFacingReason']} |"
        for metric in pack["metrics"]
    )
    path.write_text(
        f"""# Research Metrics Appendix: {pack['scenarioId']}

Claim level: `proxy`

These metrics are reproducible technical appendix evidence for the Scenario Dossier. They do not replace the buyer decision recommendation.

| Metric | Label | Claim | Formula | Official-facing reason |
|---|---|---|---|---|
{rows}

Visualization: `{pack['outputs']['htmlVisual']}`
""",
        encoding="utf-8",
    )


def _write_html_visual(path: Path, pack: dict[str, Any]) -> None:
    heatmap = pack["visualization"]["data"]
    max_value = max((row["measureCongestion"] for row in heatmap), default=1.0)
    bars = []
    for index, row in enumerate(heatmap):
        value = float(row["measureCongestion"])
        height = max(4.0, value / max_value * 130.0)
        x = 42 + index * 24
        y = 170 - height
        bars.append(
            f'<rect x="{x}" y="{y:.1f}" width="16" height="{height:.1f}" fill="#2f6f73"><title>{html.escape(row["hour"])}: {value:.1f}</title></rect>'
        )
    metric_rows = "\n".join(
        f"<tr><td>{html.escape(metric['label'])}</td><td>{html.escape(str(metric['value']))}</td><td>{html.escape(metric['formula'])}</td></tr>"
        for metric in pack["metrics"]
    )
    path.write_text(
        f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Research Metrics - {html.escape(str(pack['scenarioId']))}</title>
  <style>
    body {{ font-family: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; margin: 32px; color: #1d2528; }}
    svg {{ border: 1px solid #d8dedc; background: #f8faf9; }}
    table {{ border-collapse: collapse; margin-top: 24px; width: 100%; }}
    td, th {{ border-bottom: 1px solid #d8dedc; padding: 8px; text-align: left; vertical-align: top; }}
  </style>
</head>
<body>
  <h1>Research Metrics Appendix</h1>
  <p>Scenario: <strong>{html.escape(str(pack['scenarioId']))}</strong>. Claim level: <code>proxy</code>.</p>
  <svg width="640" height="210" role="img" aria-label="Hourly measure congestion heatmap">
    <text x="24" y="24" font-size="14" fill="#1d2528">Network-hour congestion heatmap</text>
    <line x1="36" y1="170" x2="620" y2="170" stroke="#8aa09b" />
    {''.join(bars)}
  </svg>
  <table>
    <thead><tr><th>Metric</th><th>Value</th><th>Formula</th></tr></thead>
    <tbody>{metric_rows}</tbody>
  </table>
</body>
</html>
""",
        encoding="utf-8",
    )


def _load_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _resolve_generation_context(
    *,
    dossier_path: Path,
    portfolio_matrix_path: Path,
    dossier: dict[str, Any] | None,
    input_paths: Mapping[str, str | Path] | None,
    artifact_refs: Mapping[str, str] | None,
    out_dir: Path,
) -> tuple[dict[str, Path], dict[str, str]]:
    physical_outputs = {
        "researchJson": out_dir / "research_metrics.json",
        "researchAppendix": out_dir / "dossier_appendix.md",
        "researchVisual": out_dir / "research_visual.html",
    }
    if input_paths is None:
        if artifact_refs is not None:
            raise ValueError("input_paths is required when artifact_refs is explicit")
        payload = dossier or _load_json(dossier_path)
        physical_inputs = {
            "dossierJson": dossier_path,
            "portfolioMatrix": portfolio_matrix_path,
            "baselineAnalytics": Path(payload["baseline"]["analyticsPath"]),
            "measureAnalytics": Path(payload["proposedMeasure"]["analyticsPath"]),
        }
        refs = {role: str(path) for role, path in physical_inputs.items()}
        refs.update({role: str(path) for role, path in physical_outputs.items()})
        return physical_inputs, refs

    _require_exact_roles(input_paths, set(INPUT_ROLES), map_name="input_paths")
    if artifact_refs is None:
        raise ValueError("artifact_refs is required when input_paths is explicit")
    _require_exact_roles(
        artifact_refs,
        set(INPUT_ROLES) | set(OUTPUT_ROLES),
        map_name="artifact_refs",
    )
    physical_inputs = {role: Path(input_paths[role]) for role in INPUT_ROLES}
    refs = {
        role: _logical_ref(artifact_refs[role], role=role)
        for role in INPUT_ROLES + OUTPUT_ROLES
    }
    return physical_inputs, refs


def _require_exact_roles(
    values: Mapping[str, object],
    expected: set[str],
    *,
    map_name: str,
) -> None:
    actual = set(values)
    missing = sorted(expected - actual)
    unknown = sorted(actual - expected)
    if missing or unknown:
        raise ValueError(f"Invalid {map_name}: missing={missing}, unknown={unknown}")


def _logical_ref(value: str, *, role: str) -> str:
    raw = str(value)
    path = PurePosixPath(raw)
    if (
        not raw
        or raw != raw.strip()
        or "\\" in raw
        or path.is_absolute()
        or ".." in path.parts
        or any(".staging" in part for part in path.parts)
        or (path.parts and path.parts[0].endswith(":"))
        or path.as_posix() != raw
    ):
        raise ValueError(f"Unsafe logical reference for {role}: {raw!r}")
    return path.as_posix()
