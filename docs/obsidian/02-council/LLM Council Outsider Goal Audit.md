---
title: LLM Council Outsider Goal Audit
date: 2026-06-05
project: Almaty Mobility Decision Platform
role: The Outsider
tags:
  - almaty-traffic
  - almaty/council
  - procurement
  - ultragoal
  - ai-agent/audit
aliases:
  - Outsider Goal Audit
  - Municipal Decision Platform Goal Audit
---

# LLM Council Outsider Goal Audit

Related context: [[README_VALIDATION]], [[analytics_contract]], [[.omx/ultragoal/goals.json|ultragoal goals]]

## Goal Audits

| Goal | What is unclear to an outsider | How to make it concrete | Best implementation artifact | Acceptance signal |
|---|---|---|---|---|
| G001 Baseline MVP Inventory | "MVP surface" reads like an internal feature list. A city official needs to know what is real, what is prototype, and what is only a visual demo. | Create a capability matrix with status, evidence, data backing, corridor scope, and visible screenshot/API proof for each claim. | `docs/baseline_mvp_inventory.md` plus a `reports/pitch-screenshots/manifest.json` and smoke-test checklist. | A new reviewer can run the app, call the core APIs, and mark every claimed capability as proven, partial, or demo-only. |
| G002 Scenario Dossier MVP | "Dossier" could mean research report, sales deck, tender appendix, or export. RU/KZ readiness and the required official decision are not fixed. | Define one official template for 1-2 corridors: problem, baseline, proposed measure, KPI deltas, assumptions, source confidence, risks, CAPEX/OPEX, recommendation. | `docs/scenario_dossier_template.md`, `src/traffic_sim/dossier.py`, `src/app/api/dossier/route.ts`, PDF/XLSX export artifacts. | One Abay or Al-Farabi scenario produces a RU/KZ-ready dossier with baseline-vs-measure KPIs, source list, assumptions, and export files. |
| G003 ScenarioPortfolio And Batch Runner | "Portfolio" sounds financial unless it is clearly a catalog of municipal measures. It is unclear whether it stores scenarios, runs, or investment options. | Use a structured `ScenarioMeasure` and `ScenarioPortfolio` schema with IDs, corridor, affected links, intervention type, cost envelope, constraints, and target KPIs. | `data/scenarios/almaty_portfolio.json`, `src/traffic_sim/scenario_portfolio.py`, `scripts/run_scenario_portfolio.py`. | A batch run executes 3 named municipal measures and emits comparable JSON/CSV KPI summaries. |
| G004 Executive KPI Layer | Current KPI language is simulation-centric. Officials need effects, money, bus service, risk, and confidence rather than only congestion/trip metrics. | Freeze an executive KPI schema with units, formula, owner, placeholder flag, baseline value, measure value, delta, and confidence. | Updated `docs/analytics_contract.md`, `src/traffic_sim/executive_kpis.py`, `/api/analytics` executive section, dashboard KPI panel. | UI and API show the same 8-10 executive KPIs with units and baseline-vs-measure deltas. |
| G005 Data Trust And Audit Layer | "Trust" mixes validation, provenance, reproducibility, and limitations. Procurement reviewers need a simple run passport. | Define one run passport: source list, data versions, calibration date, observed-vs-simulated table, error bands, seed, git hash, parameters, assumptions, limitations. | `src/traffic_sim/run_metadata.py`, `data/runs/<run_id>/metadata.json`, trust panel contract, dossier metadata section. | Every generated run and dossier includes a readable metadata block that explains what can and cannot be trusted. |
| G006 Municipal Scenario Library | The listed scenarios mix incidents, construction, policy, transit, weather, and demand. Their model effects are not explicit. | Classify scenarios by type and define exact mutations to graph, demand, signals, speeds, closures, or costs. Use official labels, not simulation jargon. | `data/scenarios/library/*.json`, `src/traffic_sim/scenario_library.py`, UI selector with municipal names and model-effect notes. | At least 10 presets are visible, deterministic, dossier-ready, and each states what changes in the model. |
| G007 Operational Mode And Recommendations | "Recommendations" may sound like autonomous control. A city operator needs decision support with caveats and human approval. | Frame output as detected condition, 30/60/120 minute forecast, candidate actions, expected effect, required approval, and limitations. | `src/traffic_sim/operations.py`, `src/app/api/operations/route.ts`, operator playbook template. | Import or create one incident and receive horizon forecasts plus 2-3 ranked actions with caveats. |
| G008 Closed Decision Workflow | "Closed workflow" is abstract. Roles, statuses, handoffs, and the final post-implementation audit are not named. | Define statuses: Draft, Reviewed, Approved, Assigned, Implemented, Monitoring, Recalibrated. Map each status to role, required evidence, and next action. | `src/traffic_sim/workflow.py`, `src/app/api/workflow/route.ts`, `data/workflows/*.json`, task export CSV. | One scenario moves through all statuses and produces a forecast-vs-fact post-audit record. |
| G009 Enterprise And Procurement Readiness | "Enterprise" is too broad. Procurement reviewers need tender evidence, deployment, security, support, and operating model. | Create a yes/no procurement checklist covering roles, audit logs, scenario versions, on-prem deployment, Kazakhstan data residency, backups, SLA, training, acceptance tests. | `docs/procurement_readiness.md`, `docker-compose.yml`, role/audit prototype only where needed for proof. | A tender checklist can be reviewed with linked proof files for each claim. |
| G010 Real Data Integrations | "Real data" can create legal and access confusion. Public data, city-provided feeds, commercial APIs, and manual CSV imports are different commitments. | Split sources by legal status, provider, refresh cadence, owner, import format, and whether they are demo, public, licensed, or city-provided. | `docs/data_sources.md`, provider registry in `src/traffic_sim/traffic_providers.py`, OSM refresh path for `/api/roads`, CSV/GTFS import helpers. | At least one real source imports end-to-end and the UI/API shows provider status and freshness. |
| G011 Research Metrics And Publication Visuals | Research metrics are credible but can distract from the purchase decision. The official value of each metric is not stated. | Prioritize metrics that strengthen dossier trust or ROI. Put publication-only visuals behind a later research milestone. | `docs/research_metrics_contract.md`, `src/traffic_sim/research_metrics.py`, selected endpoint and chart components. | Each metric has a formula, deterministic test, endpoint, visualization, and one official-facing reason to exist. |
| G012 Reproducibility And Deployment | Deployment and reproducibility are mixed. A clean on-prem run and a repeatable scientific run need separate proof. | Define two checklists: "reproduce a dossier" and "run locally/on-prem." Tie both to seed, config, metadata, exported trajectories, and install commands. | `simulation.config.json`, `README_METHODS.md`, `docker-compose.yml`, `data/runs/<run_id>/`, trajectory CSV/Parquet export. | A clean checkout can run one command to reproduce a scenario report with the same seed and metadata. |

## Cross-Cutting Clarity Fixes

1. Create an official outcome dictionary that maps simulation terms to municipal terms: `agent` to vehicle or trip sample, `variant` to proposed measure, `A/B` to baseline vs measure, `recommendation` to decision-support option, `confidence` to data/model reliability.
2. Make G002 the anchor artifact. Every later goal should answer which Scenario Dossier field it improves: KPI, source trust, scenario library, cost/risk, approval workflow, export, or reproducibility.
3. Label every claim using the current [[Claim Ledger]] taxonomy: `demo`, `proxy`, `calibrated`, `real-data`, or `procurement-ready`. This prevents overselling and helps agents avoid treating placeholders as city data.
4. Add an artifact registry for AI agents: goal ID, deliverable path, API route, data input, verification command, screenshot/report evidence, and current status.
5. Choose the first corridor pack now: 1-2 named Almaty corridors, 2-3 measures, available data sources, official meeting output, and the exact dossier export expected at the end of the first epic.
