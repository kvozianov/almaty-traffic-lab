---
title: First Epic Execution Plan
project: Almaty Mobility Decision Platform
type: execution-plan
status: active
created: 2026-06-05
updated: 2026-06-05
tags:
  - almaty/first-epic
  - ai-agent/workbench
  - ultragoal
aliases:
  - First Sellable Epic Plan
---

# First Epic Execution Plan

## Exact Goal

Execute the first sellable epic for the Almaty Mobility Decision Platform by making the Abay corridor dossier path defensible:

`scenario config -> run metadata -> KPI JSON -> scenario dossier -> audit/procurement evidence`

The work is complete only when [[G001 - Baseline MVP Inventory]], [[G005 - Data Trust And Audit Layer]], [[G004 - Executive KPI Layer]], and [[G002 - Scenario Dossier MVP]] have updated Agent Handoff sections, evidence links, and either a working first Scenario Dossier path or a precise blocker.

## Implementation Sequence

1. [[G001 - Baseline MVP Inventory]]
   - Create or update `docs/baseline_mvp_inventory.md`.
   - Create or update `reports/pitch-screenshots/manifest.json`.
   - Classify MVP claims as `implemented`, `partial`, `stub`, or `derived`.
   - Smoke-check core files/API surfaces before claiming capability.

2. [[G005 - Data Trust And Audit Layer]]
   - Add a minimal `RunPassport` metadata path for file-based runs and dossier generation.
   - Include seed, git hash, data sources, scenario params, calibration/validation notes, limitations, and claim labels.
   - Persist run metadata under `data/runs/` when generating the first dossier.

3. [[G004 - Executive KPI Layer]]
   - Add transparent proxy formulas for person-hours, speed delta, queue/load, bus reliability, emissions, CAPEX/OPEX placeholders, ROI/payback, confidence, and claim level.
   - Keep formulas and units visible in code and `docs/analytics_contract.md`.

4. [[G002 - Scenario Dossier MVP]]
   - Use [[First Corridor Pack - Abay]] as the corridor anchor.
   - Add a file-based dossier schema/service.
   - Generate the first Abay baseline-vs-measure dossier artifact with KPI deltas, run passport, assumptions, sources, risks, limitations, cost placeholders, and one buyer decision recommendation.

## Acceptance Gates

| Stage | Acceptance Gate |
|---|---|
| G001 | Baseline inventory and screenshot/API manifest exist; every demo claim is labeled as implemented, partial, stub, or derived; no claim exceeds [[Claim Ledger]]. |
| G005 | A generated run has a run passport with reproducibility metadata, source list, calibration notes, limitations, scenario params, and claim labels. |
| G004 | A shared executive KPI block exists with names, units, formulas, baseline/measure values, deltas, confidence, and proxy labels. |
| G002 | One Abay dossier exports Markdown/HTML plus KPI JSON/CSV-ready data and includes baseline, proposed measure, deltas, assumptions, sources, risks, cost placeholders, trust metadata, limitations, and recommendation. |

## Files Expected To Touch

- `docs/baseline_mvp_inventory.md`
- `docs/analytics_contract.md`
- `docs/obsidian/00-command-center/First Epic Execution Plan.md`
- `docs/obsidian/01-goals/G001 - Baseline MVP Inventory.md`
- `docs/obsidian/01-goals/G005 - Data Trust And Audit Layer.md`
- `docs/obsidian/01-goals/G004 - Executive KPI Layer.md`
- `docs/obsidian/01-goals/G002 - Scenario Dossier MVP.md`
- `docs/obsidian/03-registries/Artifact Registry.md`
- `docs/obsidian/03-registries/Claim Ledger.md`
- `reports/pitch-screenshots/manifest.json`
- `data/scenarios/dossier_abay_signal.json`
- `data/runs/`
- `reports/dossiers/abay-signal-retiming/`
- `src/traffic_sim/run_metadata.py`
- `src/traffic_sim/executive_kpis.py`
- `src/traffic_sim/dossier.py`
- `src/traffic_sim/analytics.py`
- `scripts/generate_dossier.py`
- `src/app/api/dossier/route.ts` if a Next API wrapper is feasible inside the stage budget.

## Verification Commands And Artifacts

- `python -m compileall src/traffic_sim scripts`
- `python scripts/generate_dossier.py --config data/scenarios/dossier_abay_signal.json`
- `npm run lint`
- `npm run build` if app/API changes require app-level verification.
- Validate `.base` files as YAML if edited.
- Validate `.canvas` files as JSON if edited.

Expected generated artifacts:

- `docs/baseline_mvp_inventory.md`
- `reports/pitch-screenshots/manifest.json`
- `data/runs/abay-signal-retiming-run-passport.json`
- `reports/dossiers/abay-signal-retiming/dossier.json`
- `reports/dossiers/abay-signal-retiming/dossier.md`
- `reports/dossiers/abay-signal-retiming/dossier.html`
- `reports/dossiers/abay-signal-retiming/kpis.csv`

## Checkpoint Rules

- After every stage, write a dated checkpoint in this note and in the relevant G00X Agent Handoff.
- Every checkpoint must include what changed, files touched, verification command or artifact, unresolved risks, claim labels changed, and next action.
- Update [[Artifact Registry]] for every created artifact, route, export, manifest, or evidence file.
- Update [[Claim Ledger]] only when evidence changes a claim level. Do not silently upgrade claims.
- Keep all high-level vault note references as wikilinks.
- Checkpoint `.omx/ultragoal/ledger.jsonl` after each completed OMX story with fresh Codex goal state.

## Current Risks

- Existing data includes cached/static or generated files; buyer-facing wording must not imply live city feeds.
- KPI formulas are transparent proxies unless supported by real calibration or source evidence.
- Existing dashboard/API surfaces may be partially implemented or derived; G001 must label them truthfully.
- PDF/Excel polish is lower priority than a stable JSON/Markdown/HTML dossier contract.
- The existing `.omx/ultragoal` plan contains later goals, but this run must not jump to G003-G012 until G002 is met or blocked.

## Handoff Format For Next Agent

For each stage, update the relevant goal note with:

- `next_action`
- what changed
- touched files
- verification command or generated artifact
- unresolved risks
- claim labels changed
- evidence links

If interrupted, the next agent should resume from this note, then read the latest Agent Handoff sections for G001/G005/G004/G002, [[Artifact Registry]], [[Claim Ledger]], and `.omx/ultragoal/ledger.jsonl`.

## Stage Checkpoints

### 2026-06-05 - Plan Created

- Changed: created this execution plan from AGENTS.md, command-center notes, council audit, registries, corridor pack, and G001/G005/G004/G002 goal notes.
- Files touched: `docs/obsidian/00-command-center/First Epic Execution Plan.md`.
- Verification: pending implementation.
- Unresolved risks: implementation details still need repo inspection and target-command discovery.
- Next action: start G001 baseline inventory and evidence manifest.

### 2026-06-05 - G001 Baseline Inventory

- Changed: created `docs/baseline_mvp_inventory.md` and `reports/pitch-screenshots/manifest.json`; classified current MVP surfaces as implemented, partial, stub, or derived.
- Files touched: `docs/baseline_mvp_inventory.md`, `reports/pitch-screenshots/manifest.json`, `docs/obsidian/01-goals/G001 - Baseline MVP Inventory.md`, `docs/obsidian/03-registries/Artifact Registry.md`, `docs/obsidian/03-registries/Claim Ledger.md`.
- Verification: `python3 -m compileall -q src/traffic_sim scripts` passed; `python3 scripts/generate_analytics.py --pattern normal --closed_streets abay` passed; screenshot dimensions and hashes recorded.
- Unresolved risks: Next app lint/build and browser smoke remain pending until later code/API changes; current analytics are proxy/stochastic.
- Next action: implement [[G005 - Data Trust And Audit Layer]] run passport metadata.

### 2026-06-05 - G005 Run Passport

- Changed: added `RunPassport` metadata builder/writer, attached it to FastAPI run metadata, and generated the first Abay signal-retiming passport.
- Files touched: `src/traffic_sim/run_metadata.py`, `src/traffic_sim/web_app.py`, `data/runs/abay-signal-retiming-run-passport.json`, `docs/obsidian/01-goals/G005 - Data Trust And Audit Layer.md`, `docs/obsidian/03-registries/Artifact Registry.md`, `docs/obsidian/03-registries/Claim Ledger.md`.
- Verification: `PYTHONPATH=src python3 -m compileall -q src/traffic_sim scripts` passed; `python3 -m json.tool data/runs/abay-signal-retiming-run-passport.json` passed.
- Unresolved risks: FastAPI smoke is blocked by missing `fastapi` in the shell environment; observed-vs-simulated rows are not yet attached per run.
- Next action: implement [[G004 - Executive KPI Layer]] transparent KPI proxies.

### 2026-06-05 - G004 Executive KPIs

- Changed: added shared executive KPI proxy formulas and generated KPI blocks into baseline and Abay analytics JSON.
- Files touched: `src/traffic_sim/executive_kpis.py`, `scripts/generate_analytics.py`, `src/traffic_sim/analytics.py`, `docs/analytics_contract.md`, `data/analytics_normal.json`, `data/analytics_normal_report.csv`, `data/analytics_normal_abay.json`, `data/analytics_normal_abay_report.csv`, `docs/obsidian/01-goals/G004 - Executive KPI Layer.md`, `docs/obsidian/03-registries/Artifact Registry.md`, `docs/obsidian/03-registries/Claim Ledger.md`.
- Verification: compileall passed; analytics generation for baseline and Abay passed; JSON validation passed; inline KPI assertions passed.
- Unresolved risks: ROI/payback are proxy values using placeholder CAPEX/OPEX and value-of-time assumptions.
- Next action: implement [[G002 - Scenario Dossier MVP]] with KPI and run-passport evidence.

### 2026-06-05 - G002 Abay Scenario Dossier

- Changed: implemented file-based Scenario Dossier generation for Abay signal retiming, including config, run passport, executive KPI block, JSON/Markdown/HTML dossier exports, KPI CSV, and a Next API wrapper.
- Files touched: `data/scenarios/dossier_abay_signal.json`, `src/traffic_sim/dossier.py`, `scripts/generate_dossier.py`, `src/app/api/dossier/route.ts`, `reports/dossiers/abay-signal-retiming/`, `data/runs/abay-signal-retiming-run-passport.json`, `docs/obsidian/01-goals/G002 - Scenario Dossier MVP.md`, `docs/obsidian/03-registries/Artifact Registry.md`, `docs/obsidian/03-registries/Claim Ledger.md`, `docs/obsidian/03-registries/First Corridor Pack - Abay.md`.
- Verification: compileall passed; `python3 scripts/generate_dossier.py --config data/scenarios/dossier_abay_signal.json` passed; dossier/config/passport JSON validation passed; KPI CSV has 12 rows.
- Recommendation: `defer`.
- Unresolved risks: Next API wrapper needs lint/build/API smoke; FastAPI smoke blocked by missing `fastapi`; dossier remains proxy-level due missing observed validation and sourced cost evidence.
- Next action: run final verification, clean/review, and record residual risks.

### 2026-06-05 - Final Verification And QA

- Changed: verified the G002 API wrapper and recorded a bounded UltraQA-style adversarial matrix for the dossier boundary.
- Files touched: `docs/obsidian/00-command-center/First Epic Execution Plan.md`, `docs/obsidian/01-goals/G002 - Scenario Dossier MVP.md`, `docs/obsidian/03-registries/Artifact Registry.md`.
- Verification: `npm run lint` passed; `npm run build` passed; `curl http://localhost:3010/api/dossier` passed against `PORT=3010 npm run dev`; in-app Browser loaded `/` and captured `/tmp/almaty-dossier-smoke-root.png`; `PYTHONPATH=src python3 -m compileall -q src/traffic_sim scripts` passed; normal dossier CLI generation passed; malformed JSON config exited nonzero; measure analytics without `executive_kpis` exited nonzero with `ValueError: Measure analytics must include executive_kpis from G004.` Regenerated passport and dossier both carry `proxy` dossier claim.
- No `.base` or `.canvas` files were edited by this run.
- Recommendation: `defer`.
- Unresolved risks: in-app Browser raw `/api/dossier` navigation was blocked by client while `curl` succeeded; FastAPI smoke remains blocked by missing `fastapi`; dashboard logs still show duplicate React key warnings for `node_7929`; dossier remains `proxy` until observed validation and sourced cost evidence are attached.
- Next action: decide whether the next agent should polish dossier export format or strengthen the evidence tier with observed/cost inputs.

### 2026-06-05 - G003 Scenario Portfolio OMX Extension

- Changed: implemented a `ScenarioPortfolio` batch runner with three comparable Abay measures and per-measure run passports.
- Files touched: `src/traffic_sim/scenario_portfolio.py`, `scripts/run_scenario_portfolio.py`, `data/scenarios/almaty_portfolio.json`, `reports/portfolio/month1/portfolio_results.json`, `reports/portfolio/month1/kpi_matrix.csv`, `reports/portfolio/month1/analytics/`, `reports/portfolio/month1/run-passports/`, `docs/analytics_contract.md`, `docs/obsidian/01-goals/G003 - ScenarioPortfolio And Batch Runner.md`, `docs/obsidian/03-registries/Artifact Registry.md`, `docs/obsidian/03-registries/Claim Ledger.md`, `docs/obsidian/03-registries/First Corridor Pack - Abay.md`.
- Verification: compileall passed; portfolio runner passed; JSON validation passed for config/results/analytics/passports; assertion harness proved three measures, three matrix rows, 12 KPI rows per measure, `proxy` claim labels, and required comparable KPI columns.
- Claim labels changed: scenario portfolio moved to `proxy`.
- Unresolved risks: proxy effects remain planning assumptions until observed data, validation, and sourced costs are attached.
- Next action: feed portfolio measures into the municipal scenario library or real-data work.

### 2026-06-05 - G006 Municipal Scenario Library OMX Extension

- Changed: implemented 11 dossier-compatible municipal presets and exposed them through `GET /api/scenario-presets`.
- Files touched: `src/traffic_sim/scenario_library.py`, `src/traffic_sim/timeline.py`, `src/traffic_sim/web_app.py`, `src/app/api/scenario-presets/route.ts`, `data/scenarios/library/municipal_presets.json`, `data/scenarios/almaty_report_scenarios.json`, `docs/analytics_contract.md`, `docs/obsidian/01-goals/G006 - Municipal Scenario Library.md`, `docs/obsidian/03-registries/Artifact Registry.md`, `docs/obsidian/03-registries/Claim Ledger.md`, `docs/obsidian/03-registries/First Corridor Pack - Abay.md`.
- Verification: compileall passed; JSON validation passed; loader/application harness proved 11 presets, all `proxy`, all dossier-compatible, all with required model-effect keys, and deterministic active graph changes; `npm run lint` passed; `npm run build` passed; live `curl http://localhost:3011/api/scenario-presets` returned 11 presets.
- Claim labels changed: municipal scenario library moved to `proxy`.
- Unresolved risks: model effects are explicit proxy assumptions, not calibrated impacts; dashboard selectors are not yet redesigned around the municipal labels.
- Next action: use presets in operations, workflows, and future dossier selectors.

### 2026-06-05 - G007 Operational Playbook OMX Extension

- Changed: implemented a minimal operations playbook path for the Abay incident workflow: incident input -> provider observations -> affected corridors -> 30/60/120 forecasts -> ranked actions -> KPI impact -> run passport -> API response.
- Files touched: `src/traffic_sim/operations.py`, `scripts/generate_operation_playbook.py`, `data/operations/sample_incident_abay.json`, `reports/operations/abay-major-incident-playbook.json`, `reports/operations/abay-major-incident-run-passport.json`, `src/app/api/operations/route.ts`, `src/traffic_sim/web_app.py`, `docs/analytics_contract.md`, `docs/obsidian/01-goals/G007 - Operational Mode And Recommendations.md`, `docs/obsidian/03-registries/Artifact Registry.md`, `docs/obsidian/03-registries/Claim Ledger.md`, `docs/obsidian/03-registries/First Corridor Pack - Abay.md`.
- Verification: compileall passed; operation playbook CLI passed; JSON validation passed for incident/playbook/passport; assertion harness proved horizons `[30, 60, 120]`, affected corridors, ranked actions, caveats, limitations, and proxy KPI impact; `npm run lint` passed; `npm run build` passed; live GET and POST smoke on `http://localhost:3012/api/operations` passed; in-app Browser opened the route.
- Claim labels changed: operational recommendations moved from `not implemented` to `proxy`; no real-time, autonomous-control, real-data, or procurement-ready claim was added.
- Unresolved risks: `data/` is ignored by `.gitignore`, so the sample incident requires force-add or a future narrow ignore exception if committing; forecasts are deterministic proxies; dashboard UI integration is not done; real incident feeds, observed queues, signal-controller state, approval logs, and forecast-vs-fact comparison are missing.
- Next action: checkpoint OMX G007, then proceed to [[G008 - Closed Decision Workflow]].

### 2026-06-05 - G008 Closed Decision Workflow OMX Extension

- Changed: implemented a closed decision workflow from Abay dossier to post-audit, including artifact locks, transition history, engineer task CSV, monitoring plan, forecast-vs-fact audit, FastAPI route, Next route, and unit test.
- Files touched: `src/traffic_sim/workflow.py`, `scripts/generate_decision_workflow.py`, `tests/test_workflow.py`, `src/app/api/workflow/route.ts`, `src/traffic_sim/web_app.py`, `docs/analytics_contract.md`, `reports/workflows/abay-signal-retiming-decision-workflow.json`, `reports/workflows/abay-signal-retiming-decision-workflow-engineer-tasks.csv`, `reports/workflows/abay-signal-retiming-decision-workflow-monitoring.json`, `reports/workflows/abay-signal-retiming-decision-workflow-post-audit.json`, `docs/obsidian/01-goals/G008 - Closed Decision Workflow.md`, `docs/obsidian/03-registries/Artifact Registry.md`, `docs/obsidian/03-registries/Claim Ledger.md`, `docs/obsidian/03-registries/First Corridor Pack - Abay.md`.
- Verification: compileall passed; `PYTHONPATH=src python3 -m unittest tests.test_workflow` passed; workflow CLI passed; JSON validation passed for workflow/monitoring/post-audit; assertion harness proved full status path, evidence completeness, task export, artifact locks, and forecast-vs-fact items; `npm run lint` passed; `npm run build` passed and listed `/api/workflow`; live GET/POST smoke on port 3013 passed; in-app Browser opened the route.
- Claim labels changed: closed decision workflow moved to `demo`; underlying dossier and KPI claims remain `proxy`.
- Unresolved risks: workflow owners are strings, not authenticated roles; approvals are not legal signatures; deployment/monitoring are demo records; observed values are demonstrator values until replaced with field data.
- Next action: checkpoint OMX G008, then proceed to [[G009 - Enterprise And Procurement Readiness]].

### 2026-06-05 - G009 Procurement Readiness OMX Extension

- Changed: created a demo-level procurement packet: readiness document, data-source/legal posture, methods/on-prem runbook, Docker/Compose prototype config, generator, tests, and tender checklist JSON/CSV.
- Files touched: `src/traffic_sim/procurement.py`, `scripts/generate_procurement_packet.py`, `tests/test_procurement.py`, `docs/procurement_readiness.md`, `docs/data_sources.md`, `README_METHODS.md`, `Dockerfile`, `.dockerignore`, `docker-compose.yml`, `reports/procurement/tender_checklist.json`, `reports/procurement/tender_checklist.csv`, `docs/obsidian/01-goals/G009 - Enterprise And Procurement Readiness.md`, `docs/obsidian/03-registries/Artifact Registry.md`, `docs/obsidian/03-registries/Claim Ledger.md`, `docs/obsidian/03-registries/First Corridor Pack - Abay.md`.
- Verification: compileall passed; `PYTHONPATH=src python3 -m unittest tests.test_procurement` passed; procurement generator passed; JSON validation passed; assertion harness proved nine tender areas and local/on-prem run path; PyYAML parsed `docker-compose.yml`; `npm run lint` passed; `npm run build` passed.
- Blocked verification: `docker compose config` could not run because Docker is not installed in this shell.
- Claim labels changed: procurement readiness packet moved to `demo`; no production SLA/security/legal/procurement-ready claim was added.
- Unresolved risks: roles are not authenticated; audit is not append-only signed storage; compose path is not built/scanned; data residency/TCO/SLA need legal and sourced evidence.
- Next action: checkpoint OMX G009, then proceed to [[G010 - Real Data Integrations]].

### 2026-06-05 - G010 Real Data Integrations OMX Extension

- Changed: implemented data-source provider registry and road-geometry provider status; exposed `GET /api/data-sources`; enriched `GET /api/roads` with `providerStatus`; updated traffic provider statuses; wired provider registry and road status into run-passport defaults; regenerated Abay dossier/workflow/procurement artifacts after provider registry generation.
- Files touched: `src/traffic_sim/data_sources.py`, `scripts/refresh_data_sources.py`, `tests/test_data_sources.py`, `src/app/api/data-sources/route.ts`, `src/app/api/roads/route.ts`, `src/traffic_sim/traffic_providers.py`, `src/traffic_sim/web_app.py`, `src/traffic_sim/run_metadata.py`, `docs/analytics_contract.md`, `docs/data_sources.md`, `README_METHODS.md`, `reports/data_sources/provider_registry.json`, `reports/data_sources/roads_geojson_provider_status.json`, regenerated `data/runs/abay-signal-retiming-run-passport.json`, regenerated `reports/dossiers/abay-signal-retiming/`, regenerated `reports/workflows/abay-signal-retiming-decision-workflow.json`, regenerated `reports/procurement/tender_checklist.json`, `docs/obsidian/01-goals/G010 - Real Data Integrations.md`, `docs/obsidian/03-registries/Artifact Registry.md`, `docs/obsidian/03-registries/Claim Ledger.md`, `docs/obsidian/03-registries/First Corridor Pack - Abay.md`.
- Verification: compileall passed; `PYTHONPATH=src python3 -m unittest tests.test_data_sources` passed; data-source refresh CLI passed; JSON validation passed; assertion harness proved provider registry, `real-data` road geometry evidence, 2,417 features, SHA-256, and run-passport/dossier provider evidence; `npm run lint` passed; `npm run build` passed and listed `/api/data-sources`; live API smokes on port 3014 passed; in-app Browser opened `/api/data-sources`.
- Claim labels changed: cached/imported road geometry is now `real-data` snapshot with explicit non-live caveat; provider registry remains `demo`.
- Unresolved risks: no live feed, GTFS import, commercial/city legal agreement, or dashboard provider-status panel yet.
- Next action: checkpoint OMX G010, then proceed to [[G011 - Research Metrics And Publication Visuals]].

### 2026-06-05 - G011 Research Metrics And Publication Visuals OMX Extension

- Changed: implemented a dossier-adjacent research metrics pack for Abay signal retiming with five selected metrics, formulas, official-facing reasons, JSON/Markdown/HTML exports, a Next API route, a FastAPI sample route, and deterministic tests.
- Files touched: `src/traffic_sim/research_metrics.py`, `scripts/generate_research_metrics.py`, `tests/test_research_metrics.py`, `src/app/api/research-metrics/route.ts`, `src/traffic_sim/web_app.py`, `docs/research_metrics_contract.md`, `docs/analytics_contract.md`, `reports/research_metrics/abay-signal-retiming/research_metrics.json`, `reports/research_metrics/abay-signal-retiming/dossier_appendix.md`, `reports/research_metrics/abay-signal-retiming/research_visual.html`, `docs/obsidian/01-goals/G011 - Research Metrics And Publication Visuals.md`, `docs/obsidian/03-registries/Artifact Registry.md`, `docs/obsidian/03-registries/Claim Ledger.md`, `docs/obsidian/03-registries/First Corridor Pack - Abay.md`.
- Verification: compileall passed; `PYTHONPATH=src python3 -m unittest tests.test_research_metrics` passed; research metrics CLI passed; `python3 -m json.tool reports/research_metrics/abay-signal-retiming/research_metrics.json` passed; assertion harness proved required metric IDs, formulas, official-facing reasons, 24 heatmap rows, `abay-signal-retiming` matrix winner, and `proxy` claim level; `npm run lint` passed; `npm run build` passed and listed `/api/research-metrics`; live `curl http://localhost:3015/api/research-metrics` passed; in-app Browser route load passed for localhost API; direct browser `file://` visual inspection was blocked by Browser URL policy, so HTML/SVG visual proof used file assertions.
- Claim labels changed: research metrics appendix moved to `proxy`.
- Unresolved risks: metrics are appendix proxies, not observed validation; sensitivity interval is deterministic, not Monte Carlo; heatmap uses generated analytics, not detector data; dashboard research UI is not built.
- Next action: checkpoint OMX G011, then proceed to [[G012 - Reproducibility And Deployment]].

### 2026-06-05 - G012 Reproducibility And Deployment OMX Extension

- Changed: implemented the blessed one-command reproduction path for the Abay first-epic evidence pack: tracked config with embedded scenario, seed propagation, deterministic synthetic analytics, run passport, dossier, trajectory CSV, local KPI matrix, workflow/procurement/research outputs, metadata, artifact manifest, README/runbook docs, changelog, and tests.
- Files touched: `simulation.config.json`, `src/traffic_sim/config.py`, `src/traffic_sim/reproducibility.py`, `src/traffic_sim/run_metadata.py`, `src/traffic_sim/dossier.py`, `scripts/generate_analytics.py`, `scripts/reproduce_dossier.py`, `tests/test_reproducibility.py`, `README.md`, `README_METHODS.md`, `CHANGELOG.md`, `docs/analytics_contract.md`, `reports/repro/abay/metadata.json`, `reports/repro/abay/artifact_manifest.json`, `reports/repro/abay/trajectory.csv`, `reports/repro/abay/portfolio/kpi_matrix.csv`, `reports/repro/abay/run-passport.json`, `reports/repro/abay/data_sources/`, `reports/repro/abay/dossier/`, `reports/repro/abay/workflows/`, `reports/repro/abay/procurement/`, `reports/repro/abay/research_metrics/`, `docs/obsidian/01-goals/G012 - Reproducibility And Deployment.md`, `docs/obsidian/03-registries/Artifact Registry.md`, `docs/obsidian/03-registries/Claim Ledger.md`, `docs/obsidian/03-registries/First Corridor Pack - Abay.md`.
- Verification: compileall passed; `PYTHONPATH=src python3 -m unittest tests.test_reproducibility` passed; `PYTHONPATH=src python3 scripts/reproduce_dossier.py --config simulation.config.json --out reports/repro/abay` passed; metadata and manifest JSON validation passed; trajectory assertion proved 48 rows; artifact manifest proved 21 artifacts with SHA-256 hashes and road status `real-data`; run-passport assertion proved `proxy` calibration and local provider paths; path traversal rejection tests passed.
- Claim labels changed: reproducible clean run moved to `demo`; no `procurement-ready` claim was added.
- Blocked verification: `docker compose config` remains blocked because Docker is not installed in this shell.
- Unresolved risks: Docker validation remains unavailable in this shell; timestamps/git dirty count vary per machine; trajectory CSV is hourly analytics output, not raw vehicle trajectories; road geometry `real-data` evidence depends on the source snapshot being present.
- Next action: run the final Ultragoal cleanup/review/QA gate before marking the aggregate Codex goal complete.

### 2026-06-05 - G012 Final Cleanup Review Gate

- Changed: ran the mandatory scoped cleanup/review gate for G012, narrowed fallback-like exception handling, regenerated the Abay reproduction pack, and obtained independent final review results.
- Files touched: `scripts/generate_analytics.py`, `src/traffic_sim/reproducibility.py`, `src/traffic_sim/run_metadata.py`, regenerated `reports/repro/abay/`.
- Verification: compileall passed; focused suite `tests.test_data_sources tests.test_procurement tests.test_research_metrics tests.test_reproducibility tests.test_workflow` passed; reproduction CLI regenerated 21 artifacts; JSON validation passed for config, metadata, manifest, and passport; semantic assertion proved 48 trajectory rows, local KPI matrix, deterministic analytics env marker, source fingerprints, local provider registry/status paths, and `proxy` calibration; stale-overclaim scan and fallback-smell scan returned no findings; `npm run lint`, `npm run build`, and `git diff --check` passed.
- Review gate: code-review returned `APPROVE`; architecture/evidence review returned `CLEAR`; no blocking findings were reported; OMX checkpoint marked `G012-reproducibility-and-deployment` complete and reported 12/12 ultragoal stories complete.
- Claim labels changed: none; G012 remains `demo`, downstream dossier/KPI/research/trajectory outputs remain `proxy`, and cached road geometry remains `real-data` snapshot.
- Blocked verification: `docker compose config` failed with `zsh:1: command not found: docker`.
- Unresolved risks: clean checkout/container validation still needs a Docker-capable host; no procurement-ready claim should be made until that evidence and independent acceptance are attached.
- Next action: validate the one-command reproduction path in a clean checkout or Docker-capable container and attach independent acceptance evidence before any claim upgrade.
