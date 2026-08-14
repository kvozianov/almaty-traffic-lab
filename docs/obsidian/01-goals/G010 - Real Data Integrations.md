---
title: G010 - Real Data Integrations
project: Almaty Mobility Decision Platform
type: ultragoal-function
goal_id: G010
goal_title: Real Data Integrations
goal_status: completed
product_status: implemented
priority: P1
owner: Jules
first_epic: false
claim_level: partial_real_data
depends_on:
  - G005
next_action: Connect GTFS/CSV refresh and municipal/commercial adapters with legal agreements before stronger data claims.
acceptance_gate: At least one real or refreshable source imports end-to-end and reports provider status in API/UI and dossier metadata.
tags:
  - almaty/goal
  - ai-agent/workbench
aliases:
  - G010 Data Integrations
---

# G010 - Real Data Integrations

## Council Verdict

Real data is a moat, but it can also block the MVP. Build adapters with fallback and provenance before chasing every source.

## Implementation Move

Split data sources by:

- public/demo/licensed/city-provided
- provider
- refresh cadence
- legal status
- owner
- import format
- fallback behavior

## Files To Touch First

- `src/traffic_sim/traffic_providers.py`
- `src/traffic_sim/graph_cache.py`
- `scripts/fetch_almaty_roads.py`
- `src/app/api/roads/route.ts`
- `data/traffic_profiles/sample_almaty.csv`
- `data/gtfs/`

## Acceptance Gate

Provider status output shows source, availability, freshness, legal mode, and last refresh timestamp.

## Avoid

- Hard-coding commercial or city feeds before access is known.
- Calling cached OSM "live".
- Letting data integration block G002.

## Evidence Links

- [[G005 - Data Trust And Audit Layer]]
- [[Claim Ledger]]
- `src/traffic_sim/traffic_providers.py`
- `src/traffic_sim/data_sources.py`
- `scripts/refresh_data_sources.py`
- `reports/data_sources/provider_registry.json`
- `reports/data_sources/roads_geojson_provider_status.json`
- `src/app/api/data-sources/route.ts`
- `src/app/api/roads/route.ts`

## Agent Handoff

### 2026-06-05 Checkpoint

- What changed: implemented a provider registry and refreshable source-status path for cached/imported Almaty road geometry. The registry records provider, source type, legal mode, owner, path, claim label, availability, last refresh, freshness, feature count, SHA-256, fallback behavior, and limitations for road geometry, local CSV, scenario library, Yandex/2GIS placeholders, Sergek placeholder, and Onay placeholder. `GET /api/data-sources` exposes the registry. `GET /api/roads` now returns the GeoJSON with top-level `providerStatus`. Run-passport defaults now include provider registry and road provider-status evidence, and the Abay dossier/run passport were regenerated with those sources.
- Files touched: `src/traffic_sim/data_sources.py`, `scripts/refresh_data_sources.py`, `tests/test_data_sources.py`, `src/app/api/data-sources/route.ts`, `src/app/api/roads/route.ts`, `src/traffic_sim/traffic_providers.py`, `src/traffic_sim/web_app.py`, `src/traffic_sim/run_metadata.py`, `docs/analytics_contract.md`, `docs/data_sources.md`, `README_METHODS.md`, `reports/data_sources/provider_registry.json`, `reports/data_sources/roads_geojson_provider_status.json`, regenerated `data/runs/abay-signal-retiming-run-passport.json`, regenerated `reports/dossiers/abay-signal-retiming/`, regenerated `reports/workflows/abay-signal-retiming-decision-workflow.json`, regenerated `reports/procurement/tender_checklist.json`, `docs/obsidian/01-goals/G010 - Real Data Integrations.md`, `docs/obsidian/03-registries/Artifact Registry.md`, `docs/obsidian/03-registries/Claim Ledger.md`, `docs/obsidian/03-registries/First Corridor Pack - Abay.md`, `docs/obsidian/00-command-center/First Epic Execution Plan.md`.
- Verification: `PYTHONPATH=src python3 -m compileall -q src/traffic_sim scripts` passed; `PYTHONPATH=src python3 -m unittest tests.test_data_sources` passed; `PYTHONPATH=src python3 scripts/refresh_data_sources.py --out reports/data_sources` generated provider artifacts with seven providers, three available sources, and one real-data available source; JSON validation passed; assertion harness proved `roads-geojson` has `real-data` claim, 2,417 features, SHA-256, provider registry in run passport/dossier sources, and road provider-status evidence; `npm run lint` passed; `npm run build` passed and listed `/api/data-sources`; live smoke `curl http://localhost:3014/api/data-sources` returned seven providers; live smoke `curl http://localhost:3014/api/roads` returned 2,417 features and `providerStatus.claim_label=real-data`; in-app Browser opened `/api/data-sources`.
- Claim labels changed: cached/imported road geometry is now recorded as `real-data` snapshot with explicit non-live caveat. Provider registry remains `demo`; local traffic CSV remains `demo`; scenario library remains `proxy`; Yandex/2GIS/Sergek/Onay remain disconnected `demo` placeholders.
- Unresolved risks: no live traffic feed is connected; road geometry freshness is local file mtime, not a live refresh; GTFS import is still pending; commercial and municipal feeds require legal agreements; dashboard UI does not yet render provider status beyond API payloads.
- Next action: proceed to [[G011 - Research Metrics And Publication Visuals]] or [[G012 - Reproducibility And Deployment]]; for stronger data claims, add GTFS/CSV refresh and legal provider contracts.
