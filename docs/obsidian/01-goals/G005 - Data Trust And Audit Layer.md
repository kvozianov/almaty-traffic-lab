---
title: G005 - Data Trust And Audit Layer
project: Almaty Mobility Decision Platform
type: ultragoal-function
goal_id: G005
goal_title: Data Trust And Audit Layer
goal_status: completed
product_status: partial
priority: P0
owner: Shared
first_epic: true
claim_level: proxy
depends_on:
  - G001
next_action: Consume the RunPassport in G004/G002 dossier generation and rerun FastAPI smoke after Python dependencies are installed.
acceptance_gate: Every generated run and dossier includes source list, calibration evidence, seed, git hash, params, limitations, and trust status.
tags:
  - almaty/goal
  - ai-agent/workbench
  - almaty/first-epic
aliases:
  - G005 Data Trust
  - Run Passport
---

# G005 - Data Trust And Audit Layer

## Council Verdict

Without trust metadata, the platform looks like a black box. The trust layer must travel with every output, not live only in a dashboard panel.

## Implementation Move

Create `RunPassport` metadata:

- run ID
- seed
- git hash
- scenario parameters
- data source list
- data versions/freshness
- calibration date
- observed-vs-simulated error
- limitations
- claim labels

## Files To Touch First

- `src/traffic_sim/run_metadata.py`
- `src/traffic_sim/web_app.py`
- `src/traffic_sim/analytics.py`
- `src/traffic_sim/calibration.py`
- `README_VALIDATION.md`
- `data/runs/`

## Acceptance Gate

Any dossier number can be traced back to input config, model version, source assumptions, and run metadata.

## Avoid

- Decorative trust badges.
- "AI recommendation" wording without an audit trail.
- Hiding limitations because they feel commercially inconvenient.

## Evidence Links

- [[README_VALIDATION]]
- [[Claim Ledger]]
- [[G002 - Scenario Dossier MVP]]
- [[G012 - Reproducibility And Deployment]]
- `src/traffic_sim/run_metadata.py`
- `data/runs/abay-signal-retiming-run-passport.json`

## Agent Handoff

### 2026-06-05 Checkpoint

- What changed: added a reusable `RunPassport` builder/writer with seed, git hash, scenario params, source fingerprints, calibration/validation notes, limitations, and exact claim labels. Wired FastAPI run metadata to include `runPassport` for generated simulations/previews when dependencies are available. Generated the first Abay signal-retiming run-passport artifact and aligned `claimLabels.dossier` to `proxy`.
- Files touched: `src/traffic_sim/run_metadata.py`, `src/traffic_sim/web_app.py`, `data/runs/abay-signal-retiming-run-passport.json`, `docs/obsidian/01-goals/G005 - Data Trust And Audit Layer.md`, `docs/obsidian/03-registries/Artifact Registry.md`, `docs/obsidian/03-registries/Claim Ledger.md`, `docs/obsidian/00-command-center/First Epic Execution Plan.md`.
- Verification: `PYTHONPATH=src python3 -m compileall -q src/traffic_sim scripts` passed; `python3 -m json.tool data/runs/abay-signal-retiming-run-passport.json` passed; regenerated dossier/passport shows `passport.claimLabels.dossier == "proxy"`. FastAPI smoke using `traffic_sim.web_app` is blocked in this shell by missing dependency `fastapi`.
- Unresolved risks: observed-vs-simulated rows are still empty in the passport; source freshness/legal provenance is file-level only; FastAPI runtime verification needs dependencies installed.
- Claim labels changed: added evidence for "Run passport exists" at `proxy`; no claim upgraded to `procurement-ready`.
- Evidence links: `src/traffic_sim/run_metadata.py`; `data/runs/abay-signal-retiming-run-passport.json`.
- Next action: implement [[G004 - Executive KPI Layer]] and consume this passport in [[G002 - Scenario Dossier MVP]].
