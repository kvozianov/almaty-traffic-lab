---
title: Almaty Mobility Executor Audit
date: 2026-06-05
project: Almaty Mobility Decision Platform
role: The Executor
tags:
  - almaty-traffic
  - almaty/council
  - procurement
  - ultragoal
  - ai-agent/audit
aliases:
  - Executor Goal Audit
  - G001-G012 Execution Audit
---

# Almaty Mobility Executor Audit

Related: [[.omx/ultragoal/goals.json|ultragoal goals]], [[.omx/ultragoal/brief|ultragoal brief]], [[README_VALIDATION]], [[docs/analytics_contract|analytics contract]], [[First Principles Goal Audit]], [[LLM Council Outsider Goal Audit]]

## Goal Execution Cards

### G001 Baseline MVP Inventory

- First concrete task: Create `docs/baseline_mvp_inventory.md` and `reports/pitch-screenshots/manifest.json` mapping every current demo claim to status, evidence, data source, and smoke check.
- Files/modules to touch first: `src/components/TrafficMap.tsx`, `src/app/api/*`, `src/traffic_sim/web_app.py`, `src/traffic_sim/*`, `README_VALIDATION.md`, `reports/pitch-screenshots/`.
- Verification command/artifact: `npm run build`; `PYTHONPATH=src python3 -m unittest discover -s tests`; completed inventory plus screenshot manifest.
- Done definition: A new agent can run the app, call core APIs, inspect screenshots, and know exactly what is implemented, partial, stubbed, or derived.

### G002 Scenario Dossier MVP

- First concrete task: Define one dossier schema/template and generate an Abay or Al-Farabi baseline-vs-measure dossier using existing simulation analytics.
- Files/modules to touch first: `src/traffic_sim/dossier.py` new, `src/traffic_sim/web_app.py`, `src/app/api/dossier/route.ts` new, `src/components/TrafficMap.tsx`, `data/scenarios/dossier_abay_signal.json` new, `reports/dossiers/`.
- Verification command/artifact: `PYTHONPATH=src python3 -m traffic_sim.dossier --scenario data/scenarios/dossier_abay_signal.json --out reports/dossiers/abay-signal-retiming`; exported `dossier.md`, `dossier.html` or `dossier.pdf`, and `dossier.xlsx` or KPI CSV.
- Done definition: One municipal dossier contains baseline, proposed measure, KPI deltas, assumptions, sources, risks, CAPEX/OPEX placeholders, trust metadata, and a UI/API export path.

### G003 ScenarioPortfolio And Batch Runner

- First concrete task: Add `ScenarioMeasure` and `ScenarioPortfolio` schemas, then seed three municipal measures that reuse current scenario primitives.
- Files/modules to touch first: `src/traffic_sim/scenario_portfolio.py` new, `src/traffic_sim/scenarios.py`, `scripts/run_scenario_portfolio.py` new, `data/scenarios/almaty_portfolio.json` new.
- Verification command/artifact: `PYTHONPATH=src python3 scripts/run_scenario_portfolio.py --portfolio data/scenarios/almaty_portfolio.json --out reports/portfolio/month1`; generated comparable JSON and CSV.
- Done definition: One command runs at least three scenarios against a common baseline and emits a ranked KPI matrix usable by the dossier.

### G004 Executive KPI Layer

- First concrete task: Freeze an executive KPI schema and implement transparent first-order proxies for time, money, bus reliability, emissions, ROI, and confidence.
- Files/modules to touch first: `docs/analytics_contract.md`, `src/traffic_sim/executive_kpis.py` new, `src/traffic_sim/analytics.py`, `scripts/generate_analytics.py`, `src/app/api/analytics/route.ts`, `src/components/TrafficMap.tsx`.
- Verification command/artifact: `curl http://localhost:3000/api/analytics | jq '.executive_kpis'`; `PYTHONPATH=src python3 -m unittest tests.test_executive_kpis` after adding formula tests.
- Done definition: API, dashboard, portfolio runner, and dossier all use the same executive KPI block with units, baseline value, measure value, delta, confidence, and placeholder flags.

### G005 Data Trust And Audit Layer

- First concrete task: Add a run passport object and attach it to every simulation, analytics response, and exported report.
- Files/modules to touch first: `src/traffic_sim/run_metadata.py` new, `src/traffic_sim/web_app.py`, `src/traffic_sim/analytics.py`, `src/traffic_sim/calibration.py`, `README_VALIDATION.md`, `data/runs/` new.
- Verification command/artifact: `PYTHONPATH=src python3 -m unittest tests.test_run_metadata`; `jq '.seed,.gitHash,.sources,.limitations' data/runs/<run_id>/metadata.json`.
- Done definition: Every run and dossier includes source list, calibration date, observed-vs-simulated table, model error, seed, git hash, data version, scenario params, and limitations.

### G006 Municipal Scenario Library

- First concrete task: Convert current presets into a typed municipal scenario library with deterministic graph, demand, signal, cost, and risk effects.
- Files/modules to touch first: `data/scenarios/almaty_report_scenarios.json`, `data/scenarios/library/*.json` new, `src/traffic_sim/scenario_library.py` new, `src/traffic_sim/scenarios.py`, `src/traffic_sim/web_app.py`, `src/components/TrafficMap.tsx`.
- Verification command/artifact: `PYTHONPATH=src python3 -m unittest tests.test_scenario_library`; `GET /api/scenario-presets` returns at least 10 municipal presets.
- Done definition: Each preset has an official label, corridor scope, model mutation, assumptions, cost placeholder, risk note, and dossier compatibility.

### G007 Operational Mode And Recommendations

- First concrete task: Add an incident request model that returns 30/60/120 minute forecasts and action templates.
- Files/modules to touch first: `src/traffic_sim/operations.py` new, `src/traffic_sim/traffic_providers.py`, `src/traffic_sim/analytics.py`, `src/traffic_sim/web_app.py`, `src/app/api/operations/route.ts` new, `src/components/TrafficMap.tsx`.
- Verification command/artifact: `curl -X POST http://localhost:8000/api/operations/incidents -H 'Content-Type: application/json' -d @data/scenarios/incident_example.json`; generated `reports/operations/<incident_id>-playbook.json`.
- Done definition: Creating or importing an incident returns affected corridors, forecast horizons, ranked detour/signal/operator actions, expected KPI impact, approval caveats, and limitations.

### G008 Closed Decision Workflow

- First concrete task: Implement a small persisted workflow state machine for scenario decisions.
- Files/modules to touch first: `src/traffic_sim/workflow.py` new, `src/traffic_sim/web_app.py`, `src/app/api/workflow/route.ts` new, `data/workflows/` new, dossier metadata/export templates.
- Verification command/artifact: `PYTHONPATH=src python3 -m unittest tests.test_workflow`; `data/workflows/<scenario_id>.json` showing `draft -> reviewed -> approved -> assigned -> deployed -> monitored -> audited`.
- Done definition: One scenario can move through all statuses with owner, timestamp, evidence, task export, and forecast-vs-fact post-audit.

### G009 Enterprise And Procurement Readiness

- First concrete task: Create a tender checklist that maps procurement requirements to proof files, status, and gaps.
- Files/modules to touch first: `docs/procurement_readiness.md` new, `docs/data_sources.md` new, `README_METHODS.md` new, `docker-compose.yml` new, run metadata/audit helpers.
- Verification command/artifact: `docker compose config`; completed checklist covering roles, audit log, scenario versions, on-prem deployment, Kazakhstan data residency, SLA/security, training, acceptance, and 3-year TCO.
- Done definition: A municipal buyer can review a single procurement note and see what is implemented, prototype-only, documented, or planned, with linked evidence.

### G010 Real Data Integrations

- First concrete task: Define a provider registry with provenance/freshness and wire one refreshable source into API/UI output.
- Files/modules to touch first: `src/traffic_sim/traffic_providers.py`, `src/traffic_sim/graph_cache.py`, `scripts/fetch_almaty_roads.py`, `src/app/api/roads/route.ts`, `data/traffic_profiles/sample_almaty.csv`, `data/gtfs/` new.
- Verification command/artifact: `PYTHONPATH=src python3 -m unittest tests.test_data_integrations`; provider status response shows source, freshness, legal mode, and availability.
- Done definition: At least one real or refreshable data source imports end-to-end and every exposed datum carries provider, timestamp, and legal/provenance status.

### G011 Research Metrics And Publication Visuals

- First concrete task: Implement only dossier-relevant metrics first: reliability index, emissions proxy, sensitivity/confidence interval, and scenario KPI matrix.
- Files/modules to touch first: `src/traffic_sim/research_metrics.py` new, `src/traffic_sim/analytics.py`, `docs/analytics_contract.md`, `src/components/TrafficMap.tsx`, dossier appendix templates.
- Verification command/artifact: `PYTHONPATH=src python3 -m unittest tests.test_research_metrics`; generated `reports/research_metrics/<run_id>.json` plus one chart or dossier appendix.
- Done definition: Each selected metric has a formula, deterministic test, endpoint or export field, and a visible use in the dossier or trust appendix.

### G012 Reproducibility And Deployment

- First concrete task: Add the blessed reproducibility path: config, seed propagation, run artifact folder, and one command that regenerates the first dossier.
- Files/modules to touch first: `simulation.config.json` new, `src/traffic_sim/config.py`, `src/traffic_sim/run_metadata.py`, `scripts/reproduce_dossier.py` new, `docker-compose.yml` new, `README_METHODS.md` new.
- Verification command/artifact: `PYTHONPATH=src python3 scripts/reproduce_dossier.py --config simulation.config.json --out reports/repro/abay`; `docker compose config`; regenerated metadata and trajectory CSV.
- Done definition: A clean checkout can reproduce the same scenario report artifacts from a fixed seed and has a documented local/on-prem run path.

## First Month Implementation Sequence

1. Ship G001 inventory: truth table, screenshot manifest, smoke commands, and demo-protection checklist.
2. Choose the first corridor pack: Abay or Al-Farabi, one baseline, one measure, one cost placeholder, one risk list, one source list.
3. Freeze schemas: `ScenarioMeasure`, `ScenarioPortfolio`, `ExecutiveKpi`, `RunPassport`, and `Dossier`.
4. Implement G005/G012 metadata first: seed, git hash, data versions, scenario params, assumptions, limitations, artifact directory.
5. Implement G004 KPI proxies: person-hours, speed delta, queue proxy, bus reliability proxy, emissions proxy, CAPEX/OPEX, ROI/payback, confidence.
6. Implement G003 minimal portfolio runner with three measures and JSON/CSV KPI matrix output.
7. Implement G002 dossier generator as a Python service/script that writes Markdown/HTML, KPI CSV/XLSX, metadata, and a printable report.
8. Add Next/FastAPI integration: `/api/dossier` route, dashboard export button, loading/error states, and artifact path response.
9. Expand G006 only enough for sales: 8-10 municipal presets with deterministic effects and honest placeholder labels; skip deep optimization.
10. Package the month-one demo: `npm run build`, `PYTHONPATH=src python3 -m unittest discover -s tests`, generated dossier artifacts, updated procurement checklist, and fresh pitch screenshots.
