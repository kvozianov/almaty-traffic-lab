---
title: First Corridor Pack - Abay
project: Almaty Mobility Decision Platform
type: corridor-pack
status: draft
created: 2026-06-05
tags:
  - almaty/corridor-pack
  - almaty/first-epic
  - ai-agent/evidence
corridor: Abay
claim_level: proxy
aliases:
  - Abay Corridor Pack
---

# First Corridor Pack - Abay

This is the first forcing function for the platform. Use it to keep G001/G004/G005/G002 grounded.

## Decision Question

Should Almaty leadership fund, defer, or request more evidence for a traffic intervention on the Abay corridor?

## Candidate Measures

| Measure | Scenario Type | First Modeling Approach | Claim Level |
|---|---|---|---|
| Signal retiming | signal_retiming | change `signal_delay_s` on matched corridor roads | proxy |
| Capacity reduction / repair detour | capacity_reduction / closure | reduce capacity/speed or close selected roads | proxy |
| Bus priority placeholder | bus_priority | improve bus reliability proxy and reduce mixed traffic capacity where needed | proxy |

## Required Dossier Fields

- corridor and affected road IDs
- baseline conditions
- proposed measure
- KPI deltas from [[G004 - Executive KPI Layer]]
- run passport from [[G005 - Data Trust And Audit Layer]]
- assumptions and limitations
- CAPEX/OPEX placeholders
- risks and required approvals
- recommendation: fund, defer, reject, or request more evidence

## First Data Sources

| Source | Path | Current Claim Level |
|---|---|---|
| Roads | `data/almaty_roads.geojson`, `cache/graphs/full_almaty.json`, `reports/data_sources/roads_geojson_provider_status.json` | real-data |
| Scenarios | `data/scenarios/almaty_report_scenarios.json`, `data/scenarios/library/municipal_presets.json` | proxy |
| Validation | [[README_VALIDATION]] | proxy |
| Analytics | `data/analytics_normal_abay.json`, `src/traffic_sim/analytics.py` | proxy |

## Acceptance

The first corridor pack is usable when [[G002 - Scenario Dossier MVP]] can generate one Abay dossier with:

- baseline vs measure KPI table
- trust appendix
- cost/risk placeholders
- source and claim labels
- exportable report artifacts
- one clear buyer decision

## Evidence Generated

### 2026-06-05 - Abay Signal Retiming Dossier

- Scenario config: `data/scenarios/dossier_abay_signal.json`
- Run passport: `data/runs/abay-signal-retiming-run-passport.json`
- Dossier JSON: `reports/dossiers/abay-signal-retiming/dossier.json`
- Dossier Markdown: `reports/dossiers/abay-signal-retiming/dossier.md`
- Dossier HTML: `reports/dossiers/abay-signal-retiming/dossier.html`
- KPI CSV: `reports/dossiers/abay-signal-retiming/kpis.csv`
- Recommendation: `defer`
- Claim level: `proxy`
- Remaining evidence gap: observed traffic/bus/queue validation rows and sourced CAPEX/OPEX.

### 2026-06-05 - Abay Month 1 Portfolio

- Portfolio config: `data/scenarios/almaty_portfolio.json`
- Portfolio JSON: `reports/portfolio/month1/portfolio_results.json`
- KPI matrix CSV: `reports/portfolio/month1/kpi_matrix.csv`
- Measures: Abay signal retiming, Abay repair detour, Abay bus priority placeholder
- Top proxy candidate: `abay-signal-retiming`
- Claim level: `proxy`
- Remaining evidence gap: portfolio effects are explicit planning proxies until observed traffic, bus, queue, and sourced cost evidence are attached.

### 2026-06-05 - Municipal Scenario Library

- Library: `data/scenarios/library/municipal_presets.json`
- API route: `src/app/api/scenario-presets/route.ts`
- Abay presets: road repair detour, accident response, signal retiming, bus priority, dedicated bus lane, BRT connector, school zone
- Broader presets: snow/weather peak, central paid parking, central event surge, new development impact
- Claim level: `proxy`
- Remaining evidence gap: preset model effects are explicit assumptions until calibrated with observed traffic, bus, queue, weather, event, development, and cost evidence.

### 2026-06-05 - Abay Operational Playbook

- Incident input: `data/operations/sample_incident_abay.json`
- Playbook JSON: `reports/operations/abay-major-incident-playbook.json`
- Run passport: `reports/operations/abay-major-incident-run-passport.json`
- API route: `src/app/api/operations/route.ts`
- Forecast horizons: 30, 60, and 120 minutes
- Recommendation mode: ranked operator actions, not autonomous control
- Claim level: `proxy`
- Remaining evidence gap: incident is manual/demo input; stronger claims require verified incident feed, observed queue length, signal-controller state, approval logs, and post-incident forecast-vs-fact comparison.

### 2026-06-05 - Abay Closed Decision Workflow

- Workflow JSON: `reports/workflows/abay-signal-retiming-decision-workflow.json`
- Engineer tasks: `reports/workflows/abay-signal-retiming-decision-workflow-engineer-tasks.csv`
- Monitoring plan: `reports/workflows/abay-signal-retiming-decision-workflow-monitoring.json`
- Post-audit comparison: `reports/workflows/abay-signal-retiming-decision-workflow-post-audit.json`
- API route: `src/app/api/workflow/route.ts`
- Status path: `draft -> reviewed -> approved -> assigned -> deployed -> monitored -> audited`
- Claim level: `demo`
- Remaining evidence gap: owner fields are not authenticated roles; approvals are not legal signatures; observed post-audit values are demonstrator values until replaced with measured field outcomes.

### 2026-06-05 - Procurement Readiness Packet

- Procurement readiness doc: `docs/procurement_readiness.md`
- Data sources/legal posture: `docs/data_sources.md`
- Methods runbook: `README_METHODS.md`
- Tender checklist JSON: `reports/procurement/tender_checklist.json`
- Tender checklist CSV: `reports/procurement/tender_checklist.csv`
- Docker prototype: `Dockerfile`, `docker-compose.yml`
- Claim level: `demo`
- Remaining evidence gap: enterprise/security/deployment/TCO claims need authenticated roles, append-only audit storage, legal review, deployment/scanning proof, SLA terms, and sourced cost evidence.

### 2026-06-05 - Data Source Provider Registry

- Provider registry: `reports/data_sources/provider_registry.json`
- Road provider status: `reports/data_sources/roads_geojson_provider_status.json`
- API route: `src/app/api/data-sources/route.ts`
- Roads API enrichment: `src/app/api/roads/route.ts`
- Available providers: road GeoJSON, traffic CSV, scenario library
- Placeholder providers: Yandex, 2GIS, Sergek/camera, Onay
- Road feature count: 2,417
- Claim level: road geometry `real-data` snapshot; registry `demo`
- Remaining evidence gap: no live traffic feed, GTFS import, legal commercial/city feed agreement, or UI provider-status panel yet.

### 2026-06-05 - Abay Research Metrics Appendix

- Research metrics JSON: `reports/research_metrics/abay-signal-retiming/research_metrics.json`
- Dossier appendix Markdown: `reports/research_metrics/abay-signal-retiming/dossier_appendix.md`
- Research visual HTML/SVG: `reports/research_metrics/abay-signal-retiming/research_visual.html`
- API route: `src/app/api/research-metrics/route.ts`
- Selected metrics: reliability index, emissions proxy, person-hours sensitivity interval, scenario KPI matrix, network-hour heatmap
- Claim level: `proxy`
- Remaining evidence gap: appendix metrics are deterministic proxies until observed validation, calibrated emissions factors, Monte Carlo uncertainty, and reviewed research outputs are attached.

### 2026-06-05 - Abay Reproduction Pack

- Config: `simulation.config.json`
- Reproduction command: `PYTHONPATH=src python3 scripts/reproduce_dossier.py --config simulation.config.json --out reports/repro/abay`
- Metadata: `reports/repro/abay/metadata.json`
- Artifact manifest: `reports/repro/abay/artifact_manifest.json`
- Trajectory CSV: `reports/repro/abay/trajectory.csv`
- KPI matrix: `reports/repro/abay/portfolio/kpi_matrix.csv`
- Provider status evidence: `reports/repro/abay/data_sources/`
- Reproduced dossier: `reports/repro/abay/dossier/`
- Reproduced workflow/procurement/research evidence: `reports/repro/abay/workflows/`, `reports/repro/abay/procurement/`, `reports/repro/abay/research_metrics/`
- Claim level: reproduction `demo`; dossier/trajectory/research `proxy`; road geometry `real-data` snapshot
- Remaining evidence gap: Docker validation and clean-checkout verification in a separate environment; road geometry `real-data` evidence depends on the local source snapshot.

### 2026-06-10 - Abay Akimat Application Package

- Workbench route: `/scenarios/abay-signal-retiming/dossier`
- Read-only dossier API: `GET /api/dossier`
- Dossier generation boundary: `POST /api/dossiers`
- Pack export boundary: immutable `GET /api/exports/procurement-pack`; POST is hidden in production and uses the canonical release bootstrap only in explicit developer mode
- Package generator: `src/traffic_sim/akimat_pack.py`, `scripts/generate_akimat_application_pack.py`
- Package root: `reports/akimat/abay-signal-retiming/`
- Application index: `reports/akimat/abay-signal-retiming/application_package_index.json`
- Procurement pilot pack index: `reports/akimat/abay-signal-retiming/procurement_pack_index.json`
- Evidence manifest: `reports/akimat/abay-signal-retiming/evidence_manifest.json`
- Data request memo: `reports/akimat/abay-signal-retiming/data_request_memo.md`
- Data readiness: `reports/akimat/abay-signal-retiming/data_readiness.json`
- Missing evidence list: `reports/akimat/abay-signal-retiming/missing_evidence.json`
- Pilot monitoring plan: `reports/akimat/abay-signal-retiming/pilot_monitoring_plan.md`, `reports/akimat/abay-signal-retiming/pilot_monitoring_plan.json`
- Pilot acceptance criteria: `reports/akimat/abay-signal-retiming/pilot_acceptance_criteria.json`
- Scenario comparison: `reports/akimat/abay-signal-retiming/scenario_alternative_comparison.md`, `reports/akimat/abay-signal-retiming/scenario_alternative_comparison.json`
- Executive/application docs: `application_summary.md`, `application_summary.html`, `executive_brief.md`, `demo_script.md`, `slide_outline.md`, `claim_boundary.md`, `local_onprem_deployment_note.md`
- Risk register: `reports/akimat/abay-signal-retiming/risk_register.json`
- Screenshot: `reports/ui/abay-dossier-workbench.png`
- Claim level: application package `demo`; dossier/KPI/portfolio `proxy`; road geometry `real-data` snapshot
- Remaining evidence gap: observed corridor speed/count data, bus travel time/reliability, current signal timing plan, incident/roadwork history, sourced CAPEX/OPEX, nominated reviewer/data steward, legal feed permissions, authenticated decision records, and immutable evidence freeze events.

### 2026-08-11 - Controlled Portfolio Release

- Active experiment: baseline `36 s`, measure `32 s`, affected signals per trip `4`, realization factor `0.55`.
- Demand control: exact aggregate count `500 -> 500`, shared seed/base series, source primitive snapshot count `1,950`; proxy-v1 applies no demand-response scaling and makes no OD-equivalence claim.
- Occupancy boundary: person-hours use the explicit proxy occupancy `1.0`; this is not an observed Almaty occupancy estimate.
- Semantic fingerprint: `238e11b8064368a138057c3545144bd1ae00ccf7ce807b0cdcf7c985150ec8c2`.
- Promoted evidence: `reports/portfolio/current.json` -> immutable run with 11 route artifacts and 43 closed compatibility aliases.
- KPI result: average trip time `1663.46 -> 1654.66 s`; congestion `55.59 -> 55.30`; person-hours `231.036 -> 229.814`; modeled CO2 `554.487 -> 551.553 kg`.
- Recommendation: `request_more_evidence` under `M5_favorable_only` + `E1_incomplete`; no unconditional funding action.
- Showcase: `/scenarios/abay-signal-retiming/dossier`; screenshot `docs/assets/abay-dossier-portfolio.png`.
- Verification: full Python `100/100`; source slice `35/35` with 13 hashes; Next 16.3.0 lint/type/build; production dossier/page/roads/procurement-pack GET 200, unsafe/unknown road runs 400/404 and both generation POST routes 404; developer allowlisted canonical POST 201; desktop/mobile browser checks passed; independent code review `APPROVE` and architecture review `CLEAR`.
- Claim level: dossier/KPIs `proxy`; release/workflow/package `demo`; road geometry cached/imported `real-data` snapshot. No label changed.
- Remaining evidence gap: observed corridor counts/travel times, field signal plans and feasibility, bus/queue validation, sourced costs, authenticated custody, clean Git clone proof and dependency security hardening.
