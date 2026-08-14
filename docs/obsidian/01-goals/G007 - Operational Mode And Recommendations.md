---
title: G007 - Operational Mode And Recommendations
project: Almaty Mobility Decision Platform
type: ultragoal-function
goal_id: G007
goal_title: Operational Mode And Recommendations
goal_status: completed
product_status: implemented
priority: P2
owner: Shared
first_epic: false
claim_level: proxy
depends_on:
  - G003
  - G004
  - G005
next_action: Connect the playbook to verified incident feeds and observed outcome logging before any stronger claim.
acceptance_gate: Creating an incident returns forecast horizons, affected corridors, ranked actions, caveats, and limitations.
tags:
  - almaty/goal
  - ai-agent/workbench
aliases:
  - G007 Operational Mode
---

# G007 - Operational Mode And Recommendations

## Council Verdict

Operational mode can become a recurring product, but recommendations must be framed as decision support, not autonomous city control.

## Implementation Move

Create an operations API that accepts incident data and returns:

- affected corridors
- 30/60/120 minute forecast
- detour candidates
- signal phase change candidates
- public communication/action checklist
- expected KPI impact
- approval caveats
- limitations

## Files To Touch First

- `src/traffic_sim/operations.py`
- `src/traffic_sim/traffic_providers.py`
- `src/traffic_sim/analytics.py`
- `src/traffic_sim/web_app.py`
- `src/app/api/operations/route.ts`
- `src/components/TrafficMap.tsx`

## Acceptance Gate

One imported or manually created incident generates `reports/operations/<incident_id>-playbook.json`.

## Avoid

- "The city should do X" autopilot language.
- Recommendations without confidence and missing-data fields.
- Real-time promises before integrations exist.

## Evidence Links

- [[G004 - Executive KPI Layer]]
- [[G005 - Data Trust And Audit Layer]]
- [[Claim Ledger]]
- `src/traffic_sim/operations.py`
- `scripts/generate_operation_playbook.py`
- `data/operations/sample_incident_abay.json`
- `reports/operations/abay-major-incident-playbook.json`
- `reports/operations/abay-major-incident-run-passport.json`
- `src/app/api/operations/route.ts`

## Agent Handoff

### 2026-06-05 Checkpoint

- What changed: implemented a minimal G007 operational mode path for a manually created Abay incident. The path normalizes incident input, reads the existing traffic provider, matches affected corridors through the municipal scenario library, produces 30/60/120 minute proxy forecasts, ranks operator actions, includes detour/signal/public-communications candidates, attaches KPI impact through [[G004 - Executive KPI Layer]], and writes a run passport through [[G005 - Data Trust And Audit Layer]].
- Files touched: `src/traffic_sim/operations.py`, `scripts/generate_operation_playbook.py`, `data/operations/sample_incident_abay.json`, `reports/operations/abay-major-incident-playbook.json`, `reports/operations/abay-major-incident-run-passport.json`, `src/app/api/operations/route.ts`, `src/traffic_sim/web_app.py`, `docs/analytics_contract.md`, `docs/obsidian/01-goals/G007 - Operational Mode And Recommendations.md`, `docs/obsidian/03-registries/Artifact Registry.md`, `docs/obsidian/03-registries/Claim Ledger.md`, `docs/obsidian/03-registries/First Corridor Pack - Abay.md`, `docs/obsidian/00-command-center/First Epic Execution Plan.md`.
- Verification: `PYTHONPATH=src python3 -m compileall -q src/traffic_sim scripts` passed; `PYTHONPATH=src python3 scripts/generate_operation_playbook.py --incident data/operations/sample_incident_abay.json --out reports/operations` generated the playbook and passport; JSON validation passed for incident, playbook, and run passport; assertion harness proved forecast horizons `[30, 60, 120]`, affected corridors, ranked actions, detour/signal/public-communications candidates, caveats, limitations, proxy KPI impact, and `operations: proxy` passport claim; `npm run lint` passed; `npm run build` passed and listed `/api/operations`; live smoke `curl http://localhost:3012/api/operations` returned the sample playbook; live POST smoke returned a playbook for `abay-posted-incident`; in-app Browser opened `http://localhost:3012/api/operations`.
- Claim labels changed: operational recommendations moved from `not implemented` to `proxy`. No real-time, real-data, autonomous-control, or procurement-ready claim was added.
- Unresolved risks: `data/` is ignored by `.gitignore`, so `data/operations/sample_incident_abay.json` will require `git add -f` or a future narrow ignore exception if committed; forecasts are deterministic proxies, not live predictions; route smoke proved HTTP behavior but not dashboard UI integration; real incident feeds, queue observations, signal-controller state, approval logs, and post-incident outcome comparison are still missing.
- Next action: move to [[G008 - Closed Decision Workflow]] so the generated playbook can become an approval/audit workflow item, or to [[G010 - Real Data Integrations]] if the priority is stronger incident/source provenance.
