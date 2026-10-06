---
title: Claim Ledger
project: Almaty Mobility Decision Platform
type: registry
status: active
created: 2026-06-05
tags:
  - almaty/registry
  - ai-agent/evidence
aliases:
  - Claim Levels
---

# Claim Ledger

This note prevents accidental overselling. Update it whenever a claim changes level.

## Claim Taxonomy

| Claim Level | Allowed Wording | Forbidden Wording Without More Evidence |
|---|---|---|
| `demo` | "The current prototype visualizes..." | "The platform proves..." |
| `proxy` | "A transparent proxy estimates..." | "Real emissions/costs are..." |
| `calibrated` | "Compared against validation data with visible error..." | "Accurate city-wide..." |
| `real-data` | "Imported from source X at time Y..." | "Live city data" when source is cached/manual |
| `procurement-ready` | "Reproducible with evidence, limitations, and acceptance criteria..." | Any claim without run passport and acceptance proof |

## Active Claims

| Claim | Current Level | Evidence | Next Upgrade Requirement |
|---|---|---|---|
| Interactive Almaty map exists | demo | `src/components/TrafficMap.tsx`, `data/almaty_roads.geojson`, `docs/baseline_mvp_inventory.md`, `reports/pitch-screenshots/manifest.json` | App-level smoke/browser proof after current implementation |
| OSM/cache geometry exists | real-data | `data/almaty_roads.geojson`, `cache/graphs/`, `reports/data_sources/roads_geojson_provider_status.json`, `src/app/api/roads/route.ts`, [[G010 - Real Data Integrations]] | Keep wording to cached/imported road geometry snapshot; add source refresh command, OSM attribution/legal review, and freshness policy before stronger/public claims |
| Validation panel/corridor comparison exists | proxy | [[README_VALIDATION]], `data/calibration/almaty_calibration_layer.json` | attach observed-vs-sim error rows before `calibrated` wording |
| Run passport exists | proxy | `src/traffic_sim/run_metadata.py`, `data/runs/abay-signal-retiming-run-passport.json`, `reports/portfolio/current.json` | Attach observed-vs-sim rows and dependency-verified exports before procurement-ready wording; immutable release run binding is verified but is not calibration evidence |
| Scenario Dossier exists | proxy | `reports/dossiers/abay-signal-retiming/dossier.md`, `reports/dossiers/abay-signal-retiming/dossier.json`, `reports/repro/abay/pair/paired-experiment.json`, `reports/portfolio/current.json`, [[G002 - Scenario Dossier MVP]] | Buyer review, observed-vs-sim evidence, controller feasibility, and sourced costs before procurement-ready wording; controlled proxy/software checks do not upgrade the claim |
| Scenario portfolio exists | proxy | `data/scenarios/almaty_portfolio.json`, `reports/portfolio/month1/portfolio_results.json`, `reports/portfolio/month1/kpi_matrix.csv`, [[G003 - ScenarioPortfolio And Batch Runner]] | Replace proxy effects with scenario presets backed by observed data, validated model outputs, and sourced CAPEX/OPEX before stronger claims |
| Municipal scenario library exists | proxy | `data/scenarios/library/municipal_presets.json`, `src/traffic_sim/scenario_library.py`, `src/app/api/scenario-presets/route.ts`, [[G006 - Municipal Scenario Library]] | Calibrate preset effects with observed data and source-specific costs before stronger claims |
| Executive ROI/payback exists | proxy | `src/traffic_sim/executive_kpis.py`, `data/analytics_normal_abay.json`, [[G004 - Executive KPI Layer]] | Replace placeholders with sourced CAPEX/OPEX and observed benefits before stronger claims |
| Operational recommendations exist | proxy | `src/traffic_sim/operations.py`, `reports/operations/abay-major-incident-playbook.json`, `reports/operations/abay-major-incident-run-passport.json`, `src/app/api/operations/route.ts`, [[G007 - Operational Mode And Recommendations]] | Connect to verified incident feeds, observed queue/outcome data, signal-controller state, approval logs, and post-incident comparison before stronger claims |
| Closed decision workflow exists | demo | `src/traffic_sim/workflow.py`, `reports/workflows/abay-signal-retiming-decision-workflow.json`, `reports/workflows/abay-signal-retiming-decision-workflow-engineer-tasks.csv`, `reports/workflows/abay-signal-retiming-decision-workflow-post-audit.json`, `src/app/api/workflow/route.ts`, [[G008 - Closed Decision Workflow]] | Add authenticated roles, legal approval/signature policy, field work-order integration, and measured forecast-vs-fact outcomes before stronger claims |
| Procurement readiness packet exists | demo | `docs/procurement_readiness.md`, `docs/data_sources.md`, `README_METHODS.md`, `reports/procurement/tender_checklist.json`, `reports/procurement/tender_checklist.csv`, `Dockerfile`, `docker-compose.yml`, [[G009 - Enterprise And Procurement Readiness]] | Add authenticated roles, append-only audit store, legal/data-residency review, security scan, deployment proof, SLA, and sourced TCO before stronger claims |
| Data provider registry exists | demo | `src/traffic_sim/data_sources.py`, `reports/data_sources/provider_registry.json`, `src/app/api/data-sources/route.ts`, [[G010 - Real Data Integrations]] | Add live/refreshable GTFS, approved municipal/commercial feeds, legal mode evidence, and UI/provider freshness display before stronger claims |
| Research metrics appendix exists | proxy | `src/traffic_sim/research_metrics.py`, `reports/research_metrics/abay-signal-retiming/research_metrics.json`, `reports/research_metrics/abay-signal-retiming/dossier_appendix.md`, `reports/research_metrics/abay-signal-retiming/research_visual.html`, `src/app/api/research-metrics/route.ts`, [[G011 - Research Metrics And Publication Visuals]] | Add observed validation, calibrated emissions factors, Monte Carlo uncertainty, and publication-review evidence before stronger claims |
| Reproducible clean run exists | demo | `portfolio.sources.json`, `requirements.lock`, `scripts/bootstrap_portfolio.py`, `src/traffic_sim/portfolio_release.py`, `reports/portfolio/current.json`, `tests/test_portfolio_release.py`, `tests/test_portfolio_bootstrap.py`, final review `CLEAR`, [[G012 - Reproducibility And Deployment]] | `trackedProof=pending_git_authorization`; validate the curated slice from a committed clean checkout/container, add security scan evidence, and obtain independent acceptance before procurement-ready wording |
| Traffic Lab re-routes city traffic for user-chosen changes | proxy | `src/lab/engine/`, `public/model/manifest.json`, `tests/lab/engine.test.ts`, [[G014 - Almaty Traffic Lab]] | Road graph and signals are real-data; capacities, demand and calibration are proxy. Attach observed travel-time comparison by period before any `calibrated` wording |

## Agent Rule

If you create UI copy, report text, or a pitch note, use the current claim level from this ledger.

## 2026-08-11 Portfolio Release Handoff

- Evidence added: controlled Abay paired-experiment contract; one canonical reproduction configuration; explicit source primitive count (`1,950`), aggregate control (`500`) and occupancy (`1.0`) boundaries; immutable release/current-manifest boundary; rollback, contention, symlink, tamper and mixed-run regression tests; responsive manifest-only showcase; canonical screenshot.
- Files touched: `portfolio.sources.json`; `requirements.lock`; `simulation.config.json`; `data/scenarios/dossier_abay_signal.json`; `src/traffic_sim/paired_experiment.py`; `src/traffic_sim/dossier.py`; `src/traffic_sim/executive_kpis.py`; `src/traffic_sim/portfolio_release.py`; `scripts/bootstrap_portfolio.py`; route/schema/test files; `README.md`; `README_METHODS.md`; `README_VALIDATION.md`; relevant Obsidian goal/registry notes.
- Verification: full Python `100/100`; source slice 35 required/13 hashes; 11 route artifacts/43 aliases; semantic fingerprint `238e11b8064368a138057c3545144bd1ae00ccf7ce807b0cdcf7c985150ec8c2`; repeated semantic/KPI identity; immutable procurement-pack GET and production-hidden POST; Next 16.3.0 lint/type/build/API/browser checks; independent code review `APPROVE` and architecture review `CLEAR`.
- Unresolved risks: no observed Abay validation, sourced economics, authenticated decision custody, committed clean-clone proof or deployment-grade security evidence; the production dependency audit still reports eight high-severity transitive findings in the Deck.gl loader chain.
- Claim labels changed: none.
- Next action: commit the curated source slice only after explicit user authorization, then reproduce from that clean commit and begin the observed-data validation protocol.
