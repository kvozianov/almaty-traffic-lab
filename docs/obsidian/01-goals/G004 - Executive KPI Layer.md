---
title: G004 - Executive KPI Layer
project: Almaty Mobility Decision Platform
type: ultragoal-function
goal_id: G004
goal_title: Executive KPI Layer
goal_status: completed
product_status: partial
priority: P0
owner: Shared
first_epic: true
claim_level: proxy
depends_on:
  - G001
next_action: Use the executive KPI block in the first Abay dossier and add UI rendering only after the dossier contract is stable.
acceptance_gate: API, UI, and dossier render the same executive KPI block.
tags:
  - almaty/goal
  - ai-agent/workbench
  - almaty/first-epic
aliases:
  - G004 Executive KPIs
---

# G004 - Executive KPI Layer

## Council Verdict

Officials need effect, cost, service quality, and risk, not only congestion index. Use transparent proxies first, but label them honestly.

## Implementation Move

Add a shared `executive_kpis` block with:

- person-hours lost/saved
- corridor speed delta
- queue proxy
- bus reliability proxy
- CO2/NOx proxy
- CAPEX/OPEX placeholders
- ROI/payback proxy
- confidence and claim level

## Files To Touch First

- `docs/analytics_contract.md`
- `src/traffic_sim/executive_kpis.py`
- `src/traffic_sim/analytics.py`
- `scripts/generate_analytics.py`
- `src/app/api/analytics/route.ts`
- `src/components/TrafficMap.tsx`

## Acceptance Gate

`/api/analytics`, portfolio output, and dossier output all use the same KPI names, units, baseline values, measure values, deltas, and confidence fields.

## Avoid

- Academic metric overload.
- KPI values without formulas or units.
- ROI claims without placeholder/proxy labels.

## Evidence Links

- [[docs/analytics_contract]]
- [[G002 - Scenario Dossier MVP]]
- [[Claim Ledger]]
- `src/traffic_sim/executive_kpis.py`
- `data/analytics_normal_abay.json`

## Agent Handoff

### 2026-06-05 Checkpoint

- What changed: added a shared executive KPI proxy module with units, formulas, baseline/measure/delta fields, confidence, claim labels, and placeholder flags. `scripts/generate_analytics.py` now supports deterministic seed input and writes an `executive_kpis` block into analytics JSON. FastAPI run analytics also attaches `executiveKpis`.
- Files touched: `src/traffic_sim/executive_kpis.py`, `scripts/generate_analytics.py`, `src/traffic_sim/analytics.py`, `docs/analytics_contract.md`, `data/analytics_normal.json`, `data/analytics_normal_report.csv`, `data/analytics_normal_abay.json`, `data/analytics_normal_abay_report.csv`, `docs/obsidian/01-goals/G004 - Executive KPI Layer.md`, `docs/obsidian/03-registries/Artifact Registry.md`, `docs/obsidian/03-registries/Claim Ledger.md`, `docs/obsidian/00-command-center/First Epic Execution Plan.md`.
- Verification: `PYTHONPATH=src python3 -m compileall -q src/traffic_sim scripts` passed; `python3 scripts/generate_analytics.py --pattern normal --seed 7` passed; `python3 scripts/generate_analytics.py --pattern normal --closed_streets abay --seed 7` passed; `python3 -m json.tool data/analytics_normal_abay.json` passed; inline assertions for `person_hours_saved`, `queue_load_proxy`, and placeholder flags passed.
- Unresolved risks: KPI values are transparent proxies, not measured city outcomes. ROI/payback depend on placeholder CAPEX/OPEX and value-of-time assumptions.
- Claim labels changed: executive ROI/payback moved from `proxy planned` to `proxy` evidence; no procurement-ready claim.
- Evidence links: `src/traffic_sim/executive_kpis.py`; `data/analytics_normal_abay.json`; `docs/analytics_contract.md`.
- Next action: implement [[G002 - Scenario Dossier MVP]] using the shared KPI block and [[G005 - Data Trust And Audit Layer]] run passport.
