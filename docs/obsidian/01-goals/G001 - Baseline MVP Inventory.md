---
title: G001 - Baseline MVP Inventory
project: Almaty Mobility Decision Platform
type: ultragoal-function
goal_id: G001
goal_title: Baseline MVP Inventory
goal_status: completed
product_status: implemented_mostly_usable
priority: P0
owner: Shared
first_epic: true
claim_level: demo
depends_on: []
next_action: Use the inventory and manifest as the baseline evidence while building G005/G004/G002.
acceptance_gate: A new agent can verify every demo claim as implemented, partial, stub, or derived.
tags:
  - almaty/goal
  - ai-agent/workbench
  - almaty/first-epic
aliases:
  - G001 Baseline MVP Inventory
---

# G001 - Baseline MVP Inventory

## Council Verdict

The current MVP is valuable, but only if it is truthfully labeled. The risk is turning inventory into prose. The move is to create a runnable baseline with screenshots, API smoke checks, data sources, and claim levels.

## Implementation Move

Create `docs/baseline_mvp_inventory.md` and `reports/pitch-screenshots/manifest.json`.

The inventory should classify each claim as:

- `implemented`
- `partial`
- `stub`
- `derived`

## Files To Touch First

- `src/components/TrafficMap.tsx`
- `src/app/api/*`
- `src/traffic_sim/web_app.py`
- `src/traffic_sim/*`
- `README_VALIDATION.md`
- `reports/pitch-screenshots/`

## Acceptance Gate

- App can be run and core API routes checked.
- Screenshot manifest exists.
- Every claimed feature links to evidence.
- No buyer-facing claim exceeds [[Claim Ledger]].

## Avoid

- Auditing every file before proving one baseline workflow.
- Calling cached/static data "live".
- Describing prototype visuals as procurement-ready.

## Evidence Links

- [[README_VALIDATION]]
- [[Artifact Registry]]
- [[Claim Ledger]]
- `.omx/ultragoal/goals.json`
- `docs/baseline_mvp_inventory.md`
- `reports/pitch-screenshots/manifest.json`

## Agent Handoff

### 2026-06-05 Checkpoint

- What changed: created the baseline MVP inventory and screenshot evidence manifest. Classified current surfaces as `implemented`, `partial`, `stub`, or `derived` and kept buyer-facing claim levels conservative.
- Files touched: `docs/baseline_mvp_inventory.md`, `reports/pitch-screenshots/manifest.json`, `docs/obsidian/01-goals/G001 - Baseline MVP Inventory.md`, `docs/obsidian/03-registries/Artifact Registry.md`, `docs/obsidian/03-registries/Claim Ledger.md`, `docs/obsidian/00-command-center/First Epic Execution Plan.md`.
- Verification: `python3 -m compileall -q src/traffic_sim scripts` passed; `python3 scripts/generate_analytics.py --pattern normal --closed_streets abay` passed and regenerated `data/analytics_normal_abay.json` plus `data/analytics_normal_abay_report.csv`; screenshot dimensions and SHA-256 hashes recorded in `reports/pitch-screenshots/manifest.json`.
- Unresolved risks: Next app build/lint and live UI/API smoke are still pending for later implementation stages; analytics remain stochastic/proxy-generated until deterministic run metadata is added.
- Claim labels changed: no upgrades. Inventory reinforces `demo`, `proxy`, partial `real-data`, and calibrated-assumption wording from [[Claim Ledger]].
- Evidence links: `docs/baseline_mvp_inventory.md`; `reports/pitch-screenshots/manifest.json`.
- Next action: proceed to [[G005 - Data Trust And Audit Layer]] and add a run passport for dossier generation.
