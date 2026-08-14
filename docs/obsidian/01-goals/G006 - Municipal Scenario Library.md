---
title: G006 - Municipal Scenario Library
project: Almaty Mobility Decision Platform
type: ultragoal-function
goal_id: G006
goal_title: Municipal Scenario Library
goal_status: completed
product_status: implemented
priority: P1
owner: Shared
first_epic: false
claim_level: proxy
depends_on:
  - G002
  - G003
next_action: Use the scenario library as the source for portfolio expansion and future dossier selectors.
acceptance_gate: At least 10 presets are deterministic, dossier-ready, and visible through API/UI.
tags:
  - almaty/goal
  - ai-agent/workbench
aliases:
  - G006 Scenario Library
---

# G006 - Municipal Scenario Library

## Council Verdict

Akimat users think in municipal interventions, not simulation primitives. The risk is a generic template gallery.

## Implementation Move

Create scenario presets for:

- road repair
- accident
- signal retiming
- bus priority
- dedicated bus lane
- BRT corridor
- school zone
- snow/weather
- paid parking
- event surge
- new development impact

Each preset must state exact graph, demand, signal, speed, capacity, cost, and risk effects.

## Files To Touch First

- `data/scenarios/almaty_report_scenarios.json`
- `data/scenarios/library/*.json`
- `src/traffic_sim/scenario_library.py`
- `src/traffic_sim/scenarios.py`
- `src/traffic_sim/web_app.py`
- `src/components/TrafficMap.tsx`

## Acceptance Gate

`GET /api/scenario-presets` returns municipal labels, assumptions, model effects, cost placeholders, and dossier compatibility.

## Avoid

- Abstract "scenario type" names in buyer-facing UI.
- Unclear model effects.
- Ten shallow presets before the first three are reliable.

## Evidence Links

- [[First Corridor Pack - Abay]]
- [[G002 - Scenario Dossier MVP]]
- `data/scenarios/almaty_report_scenarios.json`
- `data/scenarios/library/municipal_presets.json`
- `src/traffic_sim/scenario_library.py`
- `src/app/api/scenario-presets/route.ts`

## Agent Handoff

### 2026-06-05 Checkpoint

- What changed: implemented a typed municipal scenario preset library with 11 dossier-compatible `proxy` presets: road repair, accident response, signal retiming, bus priority, dedicated bus lane, BRT corridor, school zone, snow/weather, paid parking, event surge, and new development impact. Added a loader/validator, deterministic graph-application helper, timeline support for road tags and municipal event types, a compatibility pointer from `data/scenarios/almaty_report_scenarios.json`, and a Next `GET /api/scenario-presets` route.
- Files touched: `src/traffic_sim/scenario_library.py`, `src/traffic_sim/timeline.py`, `src/traffic_sim/web_app.py`, `src/app/api/scenario-presets/route.ts`, `data/scenarios/library/municipal_presets.json`, `data/scenarios/almaty_report_scenarios.json`, `docs/obsidian/01-goals/G006 - Municipal Scenario Library.md`, `docs/obsidian/03-registries/Artifact Registry.md`, `docs/obsidian/03-registries/Claim Ledger.md`, `docs/obsidian/03-registries/First Corridor Pack - Abay.md`.
- Verification: `PYTHONPATH=src python3 -m compileall -q src/traffic_sim scripts` passed; JSON validation passed for the compatibility file and canonical municipal preset catalog; loader/assertion harness proved 11 presets, all `proxy`, all dossier-compatible, all with required graph/demand/signal/speed/capacity/cost/risk model effects, and each preset applied timeline metadata plus active graph changes on the demo graph; `npm run lint` passed; `npm run build` passed and listed `/api/scenario-presets`; live smoke `curl http://localhost:3011/api/scenario-presets` returned 11 presets with model effects and dossier compatibility.
- Claim labels changed: Municipal scenario library moved from partial/planned to `proxy`; no procurement-ready claim.
- Evidence links: `data/scenarios/library/municipal_presets.json`; `src/traffic_sim/scenario_library.py`; `src/app/api/scenario-presets/route.ts`.
- Unresolved risks: model effects are explicit proxy assumptions, not calibrated impacts; the React dashboard has not been redesigned around municipal labels; stronger claims require real data integrations and observed validation.
- Next action: feed these presets into [[G007 - Operational Mode And Recommendations]] or [[G010 - Real Data Integrations]] depending on whether the next story focuses operations or source provenance.
