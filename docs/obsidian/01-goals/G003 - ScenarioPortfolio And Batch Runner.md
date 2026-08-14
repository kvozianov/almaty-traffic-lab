---
title: G003 - ScenarioPortfolio And Batch Runner
project: Almaty Mobility Decision Platform
type: ultragoal-function
goal_id: G003
goal_title: ScenarioPortfolio And Batch Runner
goal_status: completed
product_status: implemented
priority: P1
owner: Jules
first_epic: false
claim_level: proxy
depends_on:
  - G002
  - G004
  - G005
next_action: Use portfolio output to feed future dossier selection or expand municipal scenario presets in G006.
acceptance_gate: One command runs at least three scenarios against a common baseline and emits comparable KPI JSON/CSV.
tags:
  - almaty/goal
  - ai-agent/workbench
aliases:
  - G003 ScenarioPortfolio
---

# G003 - ScenarioPortfolio And Batch Runner

## Council Verdict

This turns one simulation into a capital planning engine, but it should follow the first dossier. The core risk is hidden defaults and flaky batch runs.

## Implementation Move

Create typed portfolio configs and a deterministic runner:

- `ScenarioMeasure`
- `ScenarioPortfolio`
- shared baseline
- per-scenario run metadata
- comparable KPI matrix

## Files To Touch First

- `src/traffic_sim/scenario_portfolio.py`
- `src/traffic_sim/scenarios.py`
- `scripts/run_scenario_portfolio.py`
- `data/scenarios/almaty_portfolio.json`

## Acceptance Gate

`PYTHONPATH=src python3 scripts/run_scenario_portfolio.py --portfolio data/scenarios/almaty_portfolio.json --out reports/portfolio/month1`

The output must include JSON and CSV with comparable KPI columns.

## Avoid

- Frontend-only scenario state.
- Ad hoc script parameters that are not saved.
- Running many scenarios before three are reliable.

## Evidence Links

- [[G002 - Scenario Dossier MVP]]
- [[G004 - Executive KPI Layer]]
- [[Artifact Registry]]
- `data/scenarios/almaty_portfolio.json`
- `reports/portfolio/month1/portfolio_results.json`
- `reports/portfolio/month1/kpi_matrix.csv`

## Agent Handoff

### 2026-06-05 Checkpoint

- What changed: implemented a file-based `ScenarioPortfolio` batch runner with `ScenarioMeasure` records, shared baseline analytics, explicit `proxyEffects`, per-measure executive KPI blocks, per-measure run passports, and comparable JSON/CSV outputs. The first portfolio reuses Abay measures from [[First Corridor Pack - Abay]].
- Files touched: `src/traffic_sim/scenario_portfolio.py`, `scripts/run_scenario_portfolio.py`, `data/scenarios/almaty_portfolio.json`, `reports/portfolio/month1/portfolio_results.json`, `reports/portfolio/month1/kpi_matrix.csv`, `reports/portfolio/month1/analytics/`, `reports/portfolio/month1/run-passports/`, `docs/analytics_contract.md`, `docs/obsidian/01-goals/G003 - ScenarioPortfolio And Batch Runner.md`, `docs/obsidian/03-registries/Artifact Registry.md`, `docs/obsidian/03-registries/Claim Ledger.md`, `docs/obsidian/03-registries/First Corridor Pack - Abay.md`.
- Verification: `PYTHONPATH=src python3 -m compileall -q src/traffic_sim scripts` passed; `PYTHONPATH=src python3 scripts/run_scenario_portfolio.py --portfolio data/scenarios/almaty_portfolio.json --out reports/portfolio/month1` passed; JSON validation passed for portfolio config, result JSON, three measure analytics files, and three run passports; `reports/portfolio/month1/kpi_matrix.csv` has one header plus three scenario rows.
- Claim labels changed: Scenario portfolio moved from not implemented/demo to `proxy`; no procurement-ready claim.
- Evidence links: `reports/portfolio/month1/portfolio_results.json`; `reports/portfolio/month1/kpi_matrix.csv`; `reports/portfolio/month1/run-passports/abay-signal-retiming-run-passport.json`.
- Unresolved risks: portfolio effects are transparent planning proxies, not observed impacts; no frontend selector/API route consumes the portfolio yet; CAPEX/OPEX remain placeholders; stronger evidence requires observed traffic, queue, bus, and sourced cost inputs.
- Next action: use this portfolio as the source for [[G006 - Municipal Scenario Library]] or connect top-ranked portfolio candidates back into dossier generation.
