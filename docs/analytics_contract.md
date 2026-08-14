# Analytics Data Contract (Level 4)

## `GET /api/analytics`

Returns a strict JSON payload with the following structure:

```json
{
  "summary": {
    "average_trip_time_seconds": 1200.5,
    "congestion_index": 78.5,
    "total_active_vehicles": 1500
  },
  "node_throughput": [
    {
      "node_id": "node_1234",
      "vehicles_per_hour": 2500,
      "status": "congested"
    }
  ],
  "time_series": [
    {
      "hour": "08:00",
      "congestion_index": 85.2,
      "avg_speed_kph": 15.5
    }
  ],
  "ml_forecast": [
    {
      "offset_hours": 1,
      "predicted_congestion": 88.0,
      "confidence": 0.85
    }
  ],
  "executive_kpis": {
    "claimLevel": "proxy",
    "confidence": {
      "level": "low-medium",
      "score": 0.42,
      "claimLevel": "proxy",
      "notes": "Fixed heuristic proxy-readiness marker, not a statistical confidence estimate; observed traffic, cost, and calibration evidence are still required."
    },
    "assumptions": {
      "averageVehicleOccupancy": 1.0,
      "averageVehicleOccupancyClaimLevel": "proxy",
      "valueOfTimeKztPerHour": 2500,
      "annualizationDays": 250,
      "peakHoursPerDay": 2,
      "co2KgPerVehicleHour": 2.4,
      "noxKgPerVehicleHour": 0.006
    },
    "kpis": [
      {
        "id": "person_hours",
        "label": "Person-hours per modeled peak window",
        "unit": "person-hours",
        "baseline": 1000,
        "measure": 900,
        "delta": -100,
        "direction": "lower_is_better",
        "claimLevel": "proxy",
        "formula": "average_trip_time_seconds * modeled_vehicle_count * average_vehicle_occupancy / 3600",
        "placeholder": false,
        "available": true
      }
    ]
  }
}
```

- `summary.average_trip_time_seconds` (float): Average duration of active trips.
- `summary.congestion_index` (float): Overall city congestion level (0-100).
- `summary.total_active_vehicles` (int): Number of currently simulated vehicles.
- `node_throughput` (array): List of the most congested/busiest intersections. Status must be one of `normal`, `heavy`, or `congested`.
- `time_series` (array): 24-hour breakdown of historical or current simulated day. `hour` is formatted as `HH:00`.
- `ml_forecast` (array): Predictive congestion levels for the upcoming hours. `offset_hours` starts at 1 for the next hour.
- `executive_kpis` (object): Akimat-facing proxy KPI block. Values must include KPI `id`, `label`, `unit`, `baseline`, `measure`, `delta`, `direction`, `claimLevel`, `formula`, `placeholder`, and `available`.

## Executive KPI Proxy Formulas

All first-epic executive KPIs are `proxy` unless linked to stronger evidence in [[Claim Ledger]].

| KPI ID | Unit | Formula | Direction |
|---|---|---|---|
| `person_hours` | person-hours | `average_trip_time_seconds * modeled_vehicle_count * average_vehicle_occupancy / 3600` | lower is better |
| `person_hours_saved` | person-hours | `baseline_person_hours - measure_person_hours` | higher is better |
| `corridor_speed_delta` | km/h | `average(measure.time_series.avg_speed_kph) - average(baseline.time_series.avg_speed_kph)` | higher is better |
| `queue_load_proxy` | 0-1 load | `congestion_index / 100` | lower is better |
| `bus_reliability_proxy` | % | `clamp(95 - congestion_index * 0.45 + average_speed_kph * 0.08, 35, 98)` | higher is better |
| `co2_proxy` | kg | `vehicle_hours * 2.4 kg CO2 per vehicle-hour` | lower is better |
| `nox_proxy` | kg | `vehicle_hours * 0.006 kg NOx per vehicle-hour` | lower is better |
| `capex_placeholder` | KZT | placeholder until engineering estimate is supplied | lower is better |
| `opex_placeholder` | KZT/year | placeholder until operating estimate is supplied | lower is better |
| `annual_time_savings_proxy` | KZT/year | `max(person_hours_saved, 0) * value_of_time * peak_hours_per_day * annualization_days` | higher is better |
| `roi_proxy` | ratio | `(annual_time_savings_proxy - annual_opex) / capex` | higher is better |
| `payback_proxy` | years | `capex / (annual_time_savings_proxy - annual_opex)` | lower is better |

`averageVehicleOccupancy=1.0` is an explicit `proxy` assumption, not an observed occupancy estimate. The `confidence.score=0.42` field is a fixed low/medium readiness marker used to keep the uncalibrated state visible; it has no sampling distribution, error model, or probabilistic interpretation and must not be quoted as model accuracy.

## `GET /api/analytics/export`

Returns a CSV file with the `text/csv` content type containing the `time_series` and predicted next-hour data:

```csv
Hour,Congestion_Index,Avg_Speed_kph,Predicted_Next_Hour
08:00,85.2,15.5,88.0
```

## ScenarioPortfolio Batch Contract

G003 adds a file-based `ScenarioPortfolio` contract for municipal scenario batches. A portfolio config stores one shared baseline and at least three `ScenarioMeasure` entries with:

- `id`, `name`, `type`, `claimLevel`
- `corridor` and `geometryRefs`
- saved `scenarioParams`
- CAPEX/OPEX placeholders in `costs`
- `constraints`, `assumptions`, and `targetKpis`
- explicit `proxyEffects` used to derive the measure analytics from the common baseline

Run:

```bash
PYTHONPATH=src python3 scripts/run_scenario_portfolio.py --portfolio data/scenarios/almaty_portfolio.json --out reports/portfolio/month1
```

Outputs:

- `portfolio_results.json`: full baseline, measures, run-passport links, executive KPI blocks, and comparable matrix rows.
- `kpi_matrix.csv`: one row per scenario with comparable KPI columns such as `person_hours_saved`, `corridor_speed_delta`, `queue_load_proxy`, `bus_reliability_proxy`, `roi_proxy`, and `payback_proxy`.
- `analytics/*.json`: per-measure proxy analytics with `executive_kpis`.
- `run-passports/*.json`: per-measure run metadata with seed, git hash, data sources, scenario params, limitations, and claim labels.

All portfolio values are `proxy` until linked to observed validation and sourced cost evidence in [[Claim Ledger]].

## `GET /api/scenario-presets`

Returns the G006 municipal scenario library for API/UI selectors:

```json
{
  "presets": [
    {
      "id": "abay_signal_retiming",
      "municipalLabel": "Signal timing plan update",
      "type": "signal_retiming",
      "claimLevel": "proxy",
      "dossierCompatible": true,
      "events": [
        {
          "type": "signal_retiming",
          "road_tags": ["abay"],
          "start_time": "07:30",
          "duration_minutes": 150,
          "signal_delay_s": -4
        }
      ],
      "modelEffects": {
        "graph": ["No topology change."],
        "demand": ["Demand is unchanged."],
        "signal": ["Reduce signal delay by 4 seconds."],
        "speed": ["Speed changes are indirect."],
        "capacity": ["Capacity is unchanged."],
        "cost": ["CAPEX/OPEX placeholders."],
        "risk": ["Approvals remain unverified."]
      },
      "costs": {"capexKzt": 350000000, "opexKztPerYear": 25000000}
    }
  ],
  "claimLevel": "proxy",
  "source": "data/scenarios/library/municipal_presets.json"
}
```

Every preset must include municipal wording, explicit graph/demand/signal/speed/capacity/cost/risk effects, cost placeholders, assumptions, risks, target KPIs, and dossier compatibility.

## Operations Playbook Contract

G007 adds a proxy operational playbook path for today-level incident decisions:

```bash
PYTHONPATH=src python3 scripts/generate_operation_playbook.py --incident data/operations/sample_incident_abay.json --out reports/operations
```

Outputs:

- `reports/operations/<incident_id>-playbook.json`: operator-facing decision-support playbook.
- `reports/operations/<incident_id>-run-passport.json`: run metadata with seed, git hash, source fingerprints, scenario params, limitations, and claim labels.

### `GET /api/operations`

Generates and returns the sample Abay operational playbook from `data/operations/sample_incident_abay.json`.

### `POST /api/operations`

Accepts an incident payload and returns the generated playbook:

```json
{
  "id": "abay-major-incident",
  "type": "accident_response",
  "corridor": "abay",
  "roadTags": ["abay"],
  "severity": "major",
  "startTime": "17:20",
  "durationMinutes": 65,
  "provider": "csv",
  "providerPath": "data/traffic_profiles/sample_almaty.csv",
  "source": "manual-operator-input",
  "seed": 707
}
```

The response must include:

- affected corridors
- 30/60/120 minute forecast objects
- ranked recommended actions with confidence, approval owner, and missing-data fields
- detour candidate, signal phase candidate, and public communications action
- expected KPI impact using the executive KPI proxy block
- operator checklist
- approval caveats and limitations
- output paths and run-passport audit pointer

All G007 operational recommendations are `proxy` decision-support artifacts. They do not authorize autonomous traffic control, signal retiming, detours, closures, or public communications without human approval and stronger evidence in [[Claim Ledger]].

## Closed Decision Workflow Contract

G008 adds a file-based workflow state machine for turning a dossier into accountable city action history:

```bash
PYTHONPATH=src python3 scripts/generate_decision_workflow.py --dossier reports/dossiers/abay-signal-retiming/dossier.json --out reports/workflows
```

Required status path:

`draft -> reviewed -> approved -> assigned -> deployed -> monitored -> audited`

Outputs:

- `reports/workflows/<scenario_id>-decision-workflow.json`: full state, artifact locks, transition history, owners, evidence paths, and final audit attachment.
- `reports/workflows/<scenario_id>-decision-workflow-engineer-tasks.csv`: task export for signal engineering, operations/police coordination, data collection, and procurement cost replacement.
- `reports/workflows/<scenario_id>-decision-workflow-monitoring.json`: required observed fields and source gaps for post-implementation monitoring.
- `reports/workflows/<scenario_id>-decision-workflow-post-audit.json`: forecast-vs-fact comparison and recalibration flag.

### `GET /api/workflow`

Generates and returns the sample Abay signal-retiming workflow.

### `POST /api/workflow`

Accepts a dossier path under `reports/dossiers/*/dossier.json` and returns a workflow generated from that dossier:

```json
{
  "dossierPath": "reports/dossiers/abay-signal-retiming/dossier.json"
}
```

Every transition must include owner, timestamp, evidence path/hash, comments, next action, and `requiredEvidenceSatisfied`. The workflow itself is `demo`; underlying KPI/dossier claims remain `proxy` until observed outcome data, approval records, and sourced costs are attached in [[Claim Ledger]].

## Data Source Registry Contract

G010 adds provider status metadata for real/refreshable, demo, proxy, licensed, and municipal-placeholder sources:

```bash
PYTHONPATH=src python3 scripts/refresh_data_sources.py --out reports/data_sources
```

Outputs:

- `reports/data_sources/provider_registry.json`: all provider statuses.
- `reports/data_sources/roads_geojson_provider_status.json`: cached/imported road geometry status used by `/api/roads`.

### `GET /api/data-sources`

Returns:

```json
{
  "id": "almaty-provider-registry",
  "kind": "data-provider-registry",
  "claimLevel": "demo",
  "summary": {
    "providerCount": 7,
    "availableCount": 3,
    "realDataAvailableCount": 1,
    "refreshableSource": "roads-geojson"
  },
  "providers": []
}
```

Each provider must include `id`, `label`, `provider`, `source_type`, `legal_mode`, `owner`, `path`, `claim_label`, `available`, `last_refresh`, `freshness`, `fallback_behavior`, and `limitations`.

### `GET /api/roads`

Returns the existing GeoJSON plus a top-level `providerStatus` object for `roads-geojson`. The road source may be labeled `real-data` as a cached/imported OSM-derived geometry snapshot, but it must not be described as a live road or live traffic feed.

## Research Metrics Appendix Contract

G011 adds a dossier-adjacent research appendix, not a replacement for the executive Scenario Dossier.

Run:

```bash
PYTHONPATH=src python3 scripts/generate_research_metrics.py --dossier reports/dossiers/abay-signal-retiming/dossier.json --portfolio-matrix reports/portfolio/month1/kpi_matrix.csv --out reports/research_metrics/abay-signal-retiming
```

Outputs:

- `reports/research_metrics/abay-signal-retiming/research_metrics.json`: reproducible metric pack.
- `reports/research_metrics/abay-signal-retiming/dossier_appendix.md`: Markdown appendix for dossier citation.
- `reports/research_metrics/abay-signal-retiming/research_visual.html`: exportable HTML/SVG heatmap visual.

### `GET /api/research-metrics`

Generates and returns the default Abay research metrics pack. The response includes:

- `claimLevel: "proxy"`
- `scenarioId` and `runPassportId`
- selected metrics: `reliability_index`, `emissions_proxy`, `person_hours_sensitivity_interval`, `scenario_kpi_matrix`, and `network_hour_heatmap`
- formulas and official-facing reasons for every metric
- an HTML/SVG visualization data block with 24 hourly rows
- limitations making clear that these are technical appendix proxies, not observed validation or procurement-ready evidence

All G011 metrics remain `proxy` until observed validation, calibrated emissions factors, and stronger uncertainty analysis are attached in [[Claim Ledger]].

## Reproducibility Contract

G012 adds a blessed one-command reproduction path for the first Abay dossier evidence pack:

```bash
PYTHONPATH=src python3 scripts/reproduce_dossier.py --config simulation.config.json --out reports/repro/abay
```

The command must:

- load `simulation.config.json`
- regenerate baseline and measure analytics with the fixed seed in deterministic synthetic mode
- refresh provider status evidence
- write a reproduction scenario config from the tracked config's embedded scenario object
- generate a run passport and Scenario Dossier under `reports/repro/abay/`
- export `trajectory.csv` from baseline and measure hourly analytics time series
- write `portfolio/kpi_matrix.csv` from the reproduced dossier KPI block for the research appendix
- generate workflow, procurement, and research appendix evidence under the reproduction folder
- write `metadata.json` and `artifact_manifest.json` with paths, SHA-256 hashes, bytes, claim levels, seed, and command evidence

Required outputs:

- `reports/repro/abay/metadata.json`
- `reports/repro/abay/artifact_manifest.json`
- `reports/repro/abay/trajectory.csv`
- `reports/repro/abay/portfolio/kpi_matrix.csv`
- `reports/repro/abay/run-passport.json`
- `reports/repro/abay/data_sources/`
- `reports/repro/abay/dossier/dossier.json`
- `reports/repro/abay/dossier/kpis.csv`
- `reports/repro/abay/workflows/`
- `reports/repro/abay/procurement/`
- `reports/repro/abay/research_metrics/`

The reproduction path is `demo`; dossier, KPI, trajectory, and research values remain `proxy` unless stronger evidence is added in [[Claim Ledger]]. `metadata.json` records git hash, dirty-state summary, input fingerprints, and the deterministic analytics environment flag.
