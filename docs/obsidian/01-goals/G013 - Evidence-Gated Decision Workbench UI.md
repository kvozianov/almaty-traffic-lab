---
title: G013 - Evidence-Gated Decision Workbench UI
project: Almaty Mobility Decision Platform
type: ultragoal-function
goal_id: G013
goal_title: Evidence-Gated Decision Workbench UI
goal_status: implemented
product_status: implemented_verified
priority: P0
owner: Codex
first_epic: true
claim_level: demo
depends_on:
  - G002
  - G004
  - G005
  - G008
  - G009
  - G010
  - G012
next_action: Preserve the full audit workbench as a separate evidence route or restore deep evidence sections after the presentation screen, then add append-only decision/freeze records and one Akimat-observed corridor dataset before any claim upgrade.
acceptance_gate: A municipal user can open the Abay dossier route, inspect KPI deltas, run passport, source/claim limitations, evidence gate blockers, allowed decision actions, and export/procurement readiness without any unqualified funding claim.
tags:
  - almaty/goal
  - almaty/first-epic
  - almaty/akimat
  - almaty/ui-architecture
  - ai-agent/workbench
aliases:
  - G013 Evidence-Gated Decision Workbench
  - Abay Dossier Workbench UI
---

# G013 - Evidence-Gated Decision Workbench UI

## Council Verdict

The next product move is not more map polish. The project needs an akimat-facing decision file:

> Abay corridor -> scenario -> evidence level -> recommendation -> risks -> missing evidence -> next allowed action.

This goal converts the existing file-based [[G002 - Scenario Dossier MVP]] into a serious municipal UI that can be used in a pilot/procurement conversation.

## Implementation Move

Build:

`/scenarios/abay-signal-retiming/dossier`

The screen must be an Evidence-Gated Decision Workbench:

- dossier-first
- map as supporting evidence tab
- explicit claim labels
- run passport visible
- KPI rows with sources and limitations
- evidence blockers visible
- procurement readiness visible
- decision actions gated by current `proxy` evidence level

The first route should read from existing artifacts before adding new generation side effects.

## Product Requirements

### Workbench Sections

| Section | Purpose | Source |
|---|---|---|
| Decision header | Show corridor, measure, decision question, current recommendation, claim level. | `reports/dossiers/abay-signal-retiming/dossier.json` |
| Evidence gate | Show what is allowed at `proxy` level and what blocks `procurement-ready`. | [[Claim Ledger]] |
| KPI delta table | Show baseline, measure, delta, unit, formula, claim level, placeholder flag. | dossier `executiveKpis` |
| Run passport | Show seed, git hash, source list, scenario params, limitations. | dossier `trustMetadata` / `data/runs/abay-signal-retiming-run-passport.json` |
| Assumptions and risks | Make planning assumptions explicit. | dossier assumptions / risks |
| Data readiness | Show real-data, demo, proxy, missing data, and upgrade path. | `reports/data_sources/provider_registry.json`, [[Akimat Application Readiness Plan]] |
| Procurement readiness | Show tender checklist status and export pack links. | `reports/procurement/tender_checklist.json` |
| Workflow custody | Show status, artifact locks, owner placeholders, hashes. | `reports/workflows/abay-signal-retiming-decision-workflow.json` |
| Decision action bar | Allow investigate, defer, fund conditional, reject; block clean fund. | dossier recommendation + claim level |

### Required Components

- `ClaimBadge`
- `EvidenceGate`
- `RunPassportCard`
- `KpiDeltaTable`
- `AssumptionList`
- `ProcurementReadinessPanel`
- `DecisionActionBar`

Add small helper components only if they reduce duplication.

### UI Behavior

- Show `proxy` as the current dossier level.
- Show `real-data` only for cached/imported road geometry snapshot.
- Show traffic, analytics, cost, operational and workflow values as `demo` or `proxy`.
- Do not say "fund" as a clean decision while claim level is `proxy`.
- Preferred wording: `fund conditional on evidence`.
- Expose "what data is needed from akimat" prominently.
- Keep visual tone institutional, dense, and audit-forward.

## API Boundary To Fix

Current issue:

- `GET /api/dossier` generates artifacts and returns a short CLI summary.

Target:

- `GET /api/dossier` reads existing full dossier JSON.
- `POST /api/dossiers` generates or refreshes a dossier artifact.
- future `POST /api/evidence-packs/freeze` freezes evidence.
- any future production export mutation requires authenticated, append-only custody; the current procurement-pack POST remains developer-only and uses the canonical release transaction.

Side effects should store:

- actor placeholder
- timestamp
- input hash
- output hash
- scenario version
- claim level
- limitations

## Files To Touch First

- `src/app/scenarios/abay-signal-retiming/dossier/page.tsx`
- `src/app/api/dossier/route.ts`
- `src/components/dossier/ClaimBadge.tsx`
- `src/components/dossier/EvidenceGate.tsx`
- `src/components/dossier/RunPassportCard.tsx`
- `src/components/dossier/KpiDeltaTable.tsx`
- `src/components/dossier/AssumptionList.tsx`
- `src/components/dossier/ProcurementReadinessPanel.tsx`
- `src/components/dossier/DecisionActionBar.tsx`
- `src/app/globals.css` or a scoped CSS module if needed
- `reports/ui/`
- `docs/obsidian/00-command-center/Akimat Application Readiness Plan.md`
- `docs/obsidian/03-registries/Artifact Registry.md` if screenshots/routes/exports are created

## Acceptance Gate

G013 is complete when:

- `/scenarios/abay-signal-retiming/dossier` exists and builds.
- The route reads the Abay dossier and related evidence artifacts.
- The UI displays KPI deltas, claim labels, run passport, source list, limitations, risks, missing evidence, procurement readiness, workflow custody, and export links.
- The evidence gate blocks or de-emphasizes unqualified funding while dossier remains `proxy`.
- `GET /api/dossier` no longer creates evidence as its primary behavior, or the side-effect risk is explicitly fixed in a separate POST route.
- `npm run lint` passes.
- `npm run build` passes.
- Browser smoke screenshot is saved under `reports/ui/`.
- Relevant Obsidian notes and registries are updated.

## Avoid

- Do not build a marketing landing page.
- Do not make the map the primary screen.
- Do not use "AI proves" or "traffic will improve" wording.
- Do not claim `procurement-ready` without sourced costs, observed validation, reproducibility proof, buyer acceptance evidence, and legal/procurement review.
- Do not silently upgrade any claim label.
- Do not add broad city-scale features before the Abay decision file is convincing.

## Evidence Links

- [[Akimat Application Readiness Plan]]
- [[G002 - Scenario Dossier MVP]]
- [[G004 - Executive KPI Layer]]
- [[G005 - Data Trust And Audit Layer]]
- [[G008 - Closed Decision Workflow]]
- [[G009 - Enterprise And Procurement Readiness]]
- [[G010 - Real Data Integrations]]
- [[G012 - Reproducibility And Deployment]]
- [[Claim Ledger]]
- [[Artifact Registry]]
- [[First Corridor Pack - Abay]]
- [[LLM Council - UI Architecture Decision Workbench]]
- `reports/dossiers/abay-signal-retiming/dossier.json`
- `data/runs/abay-signal-retiming-run-passport.json`
- `reports/workflows/abay-signal-retiming-decision-workflow.json`
- `reports/procurement/tender_checklist.json`
- `reports/repro/abay/artifact_manifest.json`

## Agent Handoff

### 2026-06-15 Restored Audit Workbench And Jury-Safe Presentation Layer

- What changed: restored `/scenarios/abay-signal-retiming/dossier` as a combined presentation-and-audit route. The first viewport keeps the simple Abay decision screen for a jury or meeting, while the same route again exposes the evidence workbench below it: KPI deltas, claim labels, run passport, source list, assumptions, limitations, risks, missing evidence, workflow custody, procurement readiness, export links, and a disabled clean funding path while the dossier remains `proxy`. Visible meeting-facing labels were simplified into Russian; machine claim labels and source/path identifiers were preserved as audit evidence. Review follow-up removed silent `slice(...)` truncation from required evidence/procurement/export/run-passport lists, made the bottom decision buttons derive enabled states from `dossier.recommendation.allowedDecisions`, and changed the first-viewport decision area from action buttons into a non-writing summary.
- Files touched: `src/app/scenarios/abay-signal-retiming/dossier/page.tsx`; `src/components/dossier/AbayCorridorMap.tsx`; `src/components/dossier/DecisionActionBar.tsx`; `src/components/dossier/EvidenceGate.tsx`; `src/components/dossier/KpiDeltaTable.tsx`; `src/components/dossier/ProcurementReadinessPanel.tsx`; `src/components/dossier/AssumptionList.tsx`; `src/components/dossier/RunPassportCard.tsx`; `src/components/dossier/format.ts`; `reports/ui/abay-dossier-workbench-restored-hero-browser.png`; `reports/ui/abay-dossier-workbench-audit-section-browser.png`; `docs/obsidian/01-goals/G013 - Evidence-Gated Decision Workbench UI.md`; `docs/obsidian/03-registries/Artifact Registry.md`.
- Verification: `npm run lint` passed with pre-existing warnings in `scripts/create_ain2026_pitch_deck.mjs`; `npx tsc --noEmit --pretty false --incremental false`; `npm run build`; `PYTHONPATH=src python3 -m compileall -q src/traffic_sim scripts`; `PYTHONPATH=src .venv/bin/python -m unittest discover -s tests` ran 37 tests; `curl -sS http://localhost:3022/api/dossier` returned `proxy`, 12 KPI rows, 7 sources, run metadata, and allowed decisions without clean `fund`; `curl -sS http://localhost:3022/api/exports/procurement-pack` returned `demo`, 13 inputs, 17 outputs, 13 sections, and GET/POST boundary metadata; JSON checks passed for dossier claim gating, Akimat data readiness, and audited workflow custody; Browser smoke on `http://localhost:3022/scenarios/abay-signal-retiming/dossier` saved the hero and audit-section screenshots with no console errors and confirmed all dossier sources, run-passport sources, Akimat data requests, procurement requirements, and procurement-pack outputs are present in the DOM; `Финансировать сразу` remained disabled while allowed dossier actions were enabled.
- Generated artifacts: `reports/ui/abay-dossier-workbench-restored-hero-browser.png` (1280 x 720 browser screenshot); `reports/ui/abay-dossier-workbench-audit-section-browser.png` (1280 x 720 browser screenshot).
- Unresolved risks: the UI is still file-backed and read-only; decision buttons do not yet write append-only decision records; the audit section intentionally shows some source JSON values, paths, commands, and claim labels in their original machine form; observed Akimat speed/count, bus reliability, signal timing, incident, legal permission, and sourced CAPEX/OPEX evidence are still missing; no claim can move beyond `proxy`/`demo` without those inputs and buyer review.
- Claim labels changed: none. Scenario dossier remains `proxy`; procurement pilot pack remains `demo`; road geometry remains cached/imported `real-data`; screenshots remain `demo`.
- Next action: implement append-only `POST /api/decisions` or evidence-pack freeze records for the displayed action buttons, then attach one observed Akimat dataset before any claim-level upgrade.

### 2026-06-11 Presentation Dashboard Visual Pass

- What changed: converted `/scenarios/abay-signal-retiming/dossier` from a long evidence workbench into a one-screen meeting dashboard. The screen now has a thin municipal header, a dark interactive MapLibre/deck.gl context map for the Abay corridor, amber corridor geometry and signal points, a white dossier panel, proxy KPI rows, an evidence gate summary, CAPEX estimate, and a disabled `Финансировать` action with the dossier still gated at `proxy`.
- Files touched: `src/app/scenarios/abay-signal-retiming/dossier/page.tsx`; `src/components/dossier/AbayCorridorMap.tsx`; `src/components/dossier/AbayCorridorMap.module.css`; `reports/ui/abay-dossier-presentation-dashboard.png`; `docs/obsidian/01-goals/G013 - Evidence-Gated Decision Workbench UI.md`; `docs/obsidian/01-goals/G002 - Scenario Dossier MVP.md`; `docs/obsidian/03-registries/Artifact Registry.md`.
- Verification: `npm run lint`; `npm run build`; Browser smoke on `http://localhost:3012/scenarios/abay-signal-retiming/dossier`; final screenshot saved to `reports/ui/abay-dossier-presentation-dashboard.png` after removing the Next dev overlay from the screenshot session.
- Generated artifact: `reports/ui/abay-dossier-presentation-dashboard.png` (1280 x 633 PNG screenshot).
- Unresolved risks: this visual pass intentionally compresses the prior full evidence workbench into a meeting-first presentation screen, so run passport, source registry, workflow custody, procurement package details, and export links are no longer all visible on the same route. The KPI values shown are presentation proxy values and must not be treated as calibrated evidence. Decision actions are still display-only and do not write append-only records.
- Claim labels changed: none. Scenario dossier remains `proxy`; OSM road geometry remains `real-data`; presentation screenshot remains `demo`.
- Next action: either preserve the prior long-form evidence workbench under a separate audit route or add a compact evidence drawer after the one-screen view, then implement append-only decision/freeze records and attach observed Akimat speed/count, bus, signal, or incident data before any claim upgrade.

### 2026-06-10 Full Akimat Package Integration

- What changed: extended the implemented workbench into the full Akimat readiness package. The page includes a no-build baseline in the alternative comparison, shows cost placeholders/readiness/blocker reasons, links to `GET /api/exports/procurement-pack`, and displays the generated application package/evidence export index. The original standalone mutation contract has since been superseded: GET now reads only the promoted hash-verified artifact, while POST is hidden in production and can delegate only to the bounded canonical portfolio bootstrap in explicit developer mode.
- Files touched: `src/app/scenarios/abay-signal-retiming/dossier/page.tsx`; `src/components/dossier/types.ts`; `src/app/api/exports/procurement-pack/route.ts`; `src/traffic_sim/akimat_pack.py`; `scripts/generate_akimat_application_pack.py`; `tests/test_akimat_pack.py`; `reports/akimat/abay-signal-retiming/`; `reports/ui/abay-dossier-workbench.png`; `DESIGN.md`; `.omx/context/akimat-readiness-plan-20260610T162648Z.md`.
- Verification: the original package-generation checks passed; the current boundary is additionally covered by manifest contract tests, immutable pack tamper/alias tests, production GET/header and POST-404 smoke, developer canonical-bootstrap smoke, lint, typecheck and production build.
- Generated artifacts/screenshots: `reports/akimat/abay-signal-retiming/application_summary.md`; `application_summary.html`; `evidence_manifest.json`; `missing_evidence.json`; `pilot_acceptance_criteria.json`; `procurement_pack_index.json`; `data_request_memo.md`; `data_readiness.json`; `pilot_monitoring_plan.json`; `pilot_monitoring_plan.md`; `executive_brief.md`; `demo_script.md`; `slide_outline.md`; `risk_register.json`; `scenario_alternative_comparison.json`; `scenario_alternative_comparison.md`; `claim_boundary.md`; `local_onprem_deployment_note.md`; `application_package_index.json`; `reports/ui/abay-dossier-workbench.png`.
- Unresolved risks: still file-backed; decision actions are not persisted; pack generation is not yet an immutable audit event; no Akimat-observed operations dataset is attached; no authenticated roles, sourced costs, legal review, or security review.
- Claim labels changed: none.
- Next action: implement append-only `POST /api/decisions` or `POST /api/evidence-packs/freeze`, then attach observed speed/count or bus reliability data to support a calibrated review.

### 2026-06-10 Full Verification And Contract Tightening

- What changed: completed the required Python, npm, API, and Browser verification pass for the Abay Evidence-Gated Decision Workbench. Tightened the dossier generator so a `proxy` dossier emits `investigate_further`, `defer`, `fund_conditional_on_evidence`, and `reject` instead of clean `fund`; added a regression test for that rule; added explicit `inputArtifactPath`, `outputArtifactPath`, `inputSha256`, and `outputSha256` fields to `POST /api/dossiers`; refreshed the workflow custody lock against the final dossier hash; removed sticky action bar positioning so the screenshot does not overlay dossier content; saved the final workbench screenshot at the requested path.
- Files touched: `src/traffic_sim/dossier.py`; `tests/test_dossier.py`; `src/app/api/dossiers/route.ts`; `src/components/dossier/DecisionActionBar.tsx`; `reports/dossiers/abay-signal-retiming/dossier.json`; `reports/dossiers/abay-signal-retiming/dossier.md`; `reports/dossiers/abay-signal-retiming/dossier.html`; `reports/dossiers/abay-signal-retiming/kpis.csv`; `data/runs/abay-signal-retiming-run-passport.json`; `reports/workflows/abay-signal-retiming-decision-workflow.json`; `reports/workflows/abay-signal-retiming-decision-workflow-engineer-tasks.csv`; `reports/workflows/abay-signal-retiming-decision-workflow-monitoring.json`; `reports/workflows/abay-signal-retiming-decision-workflow-post-audit.json`; `reports/repro/abay/`; `reports/ui/abay-dossier-workbench.png`.
- Verification: `PYTHONPATH=src python3 -m compileall -q src/traffic_sim scripts`; `python3 scripts/generate_dossier.py --config data/scenarios/dossier_abay_signal.json`; `PYTHONPATH=src python3 scripts/reproduce_dossier.py --config simulation.config.json --out reports/repro/abay`; `PYTHONPATH=src .venv/bin/python -m unittest discover -s tests` ran 36 tests; `PYTHONPATH=src python3 scripts/generate_decision_workflow.py --dossier reports/dossiers/abay-signal-retiming/dossier.json --out reports/workflows`; `npm run lint`; `npm run build`; dev smoke on `http://localhost:3020/scenarios/abay-signal-retiming/dossier`; `GET /api/dossier` returned full dossier JSON with `proxy`, 12 KPI rows, trust metadata, and gated allowed decisions; `POST /api/dossiers` returned actor, timestamp, input/output artifact paths, SHA-256 hashes, claim level, limitations, and recommendation; Browser smoke confirmed no horizontal overflow, required sections visible, forbidden phrases absent, and `Unconditional fund` disabled.
- Generated artifacts: `reports/ui/abay-dossier-workbench.png` (1425 x 4968 PNG); refreshed `reports/dossiers/abay-signal-retiming/`; refreshed `data/runs/abay-signal-retiming-run-passport.json`; refreshed `reports/workflows/abay-signal-retiming-decision-workflow*`; refreshed `reports/repro/abay/metadata.json`, `reports/repro/abay/artifact_manifest.json`, `reports/repro/abay/trajectory.csv`, `reports/repro/abay/dossier/`, `reports/repro/abay/workflows/`, `reports/repro/abay/procurement/`, `reports/repro/abay/research_metrics/`, and `reports/repro/abay/data_sources/`.
- Unresolved risks: decision actions are still display-only and do not write an append-only decision record; no authenticated akimat roles or legal approvals exist; observed speed/count/bus/signal/incident data and sourced CAPEX/OPEX are still missing; POST generation returns hashes but does not yet persist a separate immutable generation event log.
- Claim labels changed: none. Scenario dossier remains `proxy`; procurement packet remains `demo`; road geometry remains a cached/imported `real-data` snapshot.
- Next action: implement authenticated `POST /api/decisions` or `POST /api/evidence-packs/freeze` with append-only custody records, then attach one observed akimat dataset before considering any claim-level upgrade.

### 2026-06-10 Implementation Verified

- What changed: implemented `/scenarios/abay-signal-retiming/dossier` as the first akimat-facing Evidence-Gated Decision Workbench. The route reads the Abay dossier, run passport, provider registry, workflow custody, procurement checklist, reproduction metadata, artifact manifest, and portfolio matrix from existing artifacts. The UI shows KPI deltas, claim badges, formulas, placeholder flags, source readiness, missing akimat data requests, run passport, workflow locks/history, procurement gaps, export paths, and an action bar that keeps unqualified funding disabled while the dossier remains `proxy`.
- Files touched: `src/app/scenarios/abay-signal-retiming/dossier/page.tsx`; `src/app/api/dossier/route.ts`; `src/app/api/dossiers/route.ts`; `src/components/dossier/ClaimBadge.tsx`; `src/components/dossier/EvidenceGate.tsx`; `src/components/dossier/RunPassportCard.tsx`; `src/components/dossier/KpiDeltaTable.tsx`; `src/components/dossier/AssumptionList.tsx`; `src/components/dossier/ProcurementReadinessPanel.tsx`; `src/components/dossier/DecisionActionBar.tsx`; `src/components/dossier/types.ts`; `src/components/dossier/format.ts`; `reports/ui/abay-dossier-workbench-g013.png`.
- Verification: `npm run lint`; `npm run build`; browser smoke on `http://localhost:3016/scenarios/abay-signal-retiming/dossier`; API smoke `curl -sS http://localhost:3016/api/dossier | jq '{id, claimLevel, kpiRows: (.executiveKpis.kpis | length), hasTrustMetadata: (.trustMetadata != null)}'` returned `abay-signal-retiming`, `proxy`, `12`, and `true`.
- Generated artifact: `reports/ui/abay-dossier-workbench-g013.png` (1440 x 1200 PNG screenshot).
- Unresolved risks: UI is file-backed and read-only; action buttons do not yet record decisions to an append-only audit log; POST `/api/dossiers` prepares the generation boundary but does not yet store input/output hash metadata beyond the generated artifact response; authenticated roles, legal approvals, security scans, sourced costs, and observed traffic/bus/signal data remain missing.
- Claim labels changed: none.
- Next action: add a decision-record POST/freeze/export boundary with actor placeholder, input hash, output hash, scenario version, claim level, and limitations, then attach one observed akimat dataset before any claim upgrade.

### 2026-06-10 Plan Created

- What changed: created G013 as the active Obsidian goal for the akimat-facing Evidence-Gated Decision Workbench UI.
- Files touched: `docs/obsidian/01-goals/G013 - Evidence-Gated Decision Workbench UI.md`, `docs/obsidian/00-command-center/Akimat Application Readiness Plan.md`, `docs/obsidian/00-command-center/Almaty Mobility Command Center.md`.
- Verification: planning note created; no code behavior changed; no claim labels upgraded.
- Unresolved risks: current dossier API uses GET for generation; UI route not implemented yet; buyer-facing procurement language still needs legal/procurement review.
- Claim labels changed: none.
- Next action: implement the route and components listed in Files To Touch First.

### 2026-08-11 - Manifest-Only Portfolio Showcase

- What changed: made the dossier page and read-only API consume only the promoted route manifest; pinned the road API and map to the same immutable run/source hash; isolated generation behind an opt-in non-production POST with an explicit child-environment allowlist; removed false decision affordances; restored Russian metadata, responsive 390 px layout, visible OSM attribution and artifact-derived release/evidence states. Updated Next.js and `eslint-config-next` to 16.3.0.
- Files touched: `src/app/layout.tsx`; `src/app/api/dossier/route.ts`; `src/app/api/dossiers/route.ts`; `src/app/api/roads/route.ts`; `src/app/scenarios/abay-signal-retiming/dossier/page.tsx`; `src/components/dossier/`; `tests/portfolio_route_manifest_contract.ts`; `tests/run_frontend_contract.mjs`; `tests/portfolio_routes_smoke.mjs`; `docs/assets/abay-dossier-portfolio.png`; `scripts/create_ain2026_pitch_deck.mjs`; `package.json`; `package-lock.json`.
- Verification: lint exited 0 with zero errors and zero warnings; TypeScript and Next 16.3.0 production build passed; developer POST boundary returned 415/400/400/400/400/413 for invalid requests and 201 for the allowlisted request; production GET/page returned 200, pinned roads returned 200 with matching run/source headers, unsafe/unknown runs returned 400/404, and POST returned 404. Desktop 1440 and mobile 390 checks found zero page overflow, visible attribution, Russian language/title, no button affordances, no console/network errors, incomplete empirical validation, and a blocked unconditional funding path.
- Generated artifact: `docs/assets/abay-dossier-portfolio.png` (1440 x 900, SHA-256 `cc4f007566fad158977ff72dc83db107c01dab6f6804f3c13d3a0b3a92c39b1d`).
- Unresolved risks: the UI is read-only and has no authenticated append-only decision record; observed evidence and sourced costs are absent; eight high-severity production audit findings remain in the transitive `@deck.gl/geo-layers` loader chain.
- Claim labels changed: none. The workbench remains `demo`, dossier/KPI values remain `proxy`, and OSM geometry is a non-live `real-data` snapshot.
- Next action: replace or upgrade the vulnerable map-loader chain before deployment; then add authenticated decision/evidence-freeze custody only after the observed-data validation path is funded.

### 2026-08-14 - English-Only Portfolio Workbench Requirement Approved

- What changed: made English-only presentation a mandatory P0 release contract. The planned public information architecture is dossier-first: `/` redirects to the canonical Abay dossier, while the current map-first experience moves to a required `/sandbox` with an above-fold `demo`/`proxy` disclaimer. The fake RUS/KAZ selector is removed; metadata, UI, map labels, accessibility names, states, print and portfolio-facing downloads must all be English.
- Files touched: `.omx/plans/portfolio-idealization-technical-specification.md`; `.omx/plans/portfolio-idealization-traceability.md`; this goal note; `docs/obsidian/03-registries/Artifact Registry.md`.
- Verification: all LANG-01..07, IA-01..05, DOS-01..10, EXP-01..06, SBX-01..05, accessibility, responsive, performance, privacy and metadata requirements map to an explicit test/evidence row; independent review returned `APPROVE`.
- Generated artifact: implementation-ready English UI, route, download and visual acceptance specification.
- Unresolved risks: no UI code changed in this planning task. The current rendered site remains Russian; sandbox mobile composition is overcrowded; current downloads expose paths rather than user actions; the Deck.gl loader chain blocks a safe public sandbox release.
- Claim labels changed: none. English wording must retain the same `demo`, `proxy` and non-live `real-data` boundaries.
- Next action: implement M1 without changing evidence authority: English app shell/states, canonical redirect, required sandbox split/disclaimer, English-only map-label policy and `tests/english_ui_contract.mjs`.

### 2026-08-14 - M1 English Dossier-First Shell Complete

- What changed: made the canonical public shell English-only and dossier-first. `/` now emits a permanent HTTP redirect to the Abay dossier; the app has an English document language, shared top navigation/footer, English metadata and recovery states, and a keyboard skip target. The previous map-first view is retained at `/sandbox` behind a persistent above-fold disclaimer that identifies it as `demo`/`proxy`, not live traffic, calibrated evidence, or a funding recommendation. All rendered dossier and map UI strings, accessibility names, and empty/error states are English; remaining Cyrillic is confined to non-rendered road-name lookup aliases needed for source geometry matching.
- Files touched: `next.config.ts`; `src/app/layout.tsx`; `src/app/page.tsx`; `src/app/loading.tsx`; `src/app/not-found.tsx`; `src/app/error.tsx`; `src/app/sandbox/page.tsx`; `src/app/scenarios/abay-signal-retiming/dossier/page.tsx`; `src/components/site/SiteHeader.tsx`; `src/components/site/SiteFooter.tsx`; `src/components/TrafficMap.tsx`; `src/components/dossier/AbayCorridorMap.tsx`; dossier presentation components; `tests/english_ui_contract.mjs`; `.omx/evidence/portfolio-m1-ultraqa.md`.
- Verification: `node tests/english_ui_contract.mjs`; `npm run lint`; `npx tsc --noEmit --pretty false --incremental false`; `npm run build`; production smoke confirmed root HTTP `308`, dossier HTTP `200` with no rendered Cyrillic, sandbox disclaimer presence, unknown route HTTP `404`, and malformed-road request HTTP `404` with `manifest_missing`.
- Generated artifact: M1 dynamic and adversarial QA matrix at `.omx/evidence/portfolio-m1-ultraqa.md`.
- Unresolved risks: the deck.gl loader dependency audit remains an M4/public-release blocker; no observed traffic or cost evidence is introduced; downloads, responsive refinement, security hardening, CI/container proof, and owner-governed release material remain later milestones.
- Claim labels changed: none. The dossier/KPIs remain `proxy`; package/workflow remain `demo`; road geometry remains a non-live `real-data` snapshot.
- Next action: complete M2 by turning the dossier’s portfolio-facing downloads into clear English actions with client-side export completion feedback, while preserving source artifact authority and claim boundaries.

### 2026-08-14 - M2 Immutable Evidence Downloads Complete

- What changed: replaced visible path cards with five explicit, English, read-only download actions and browser print/save-as-PDF. The promoted manifest now owns an exact closed download allowlist: HTML dossier, JSON evidence, KPI CSV, run passport JSON, and procurement index JSON. Each entry is bound to one run ID and includes its normalized logical path, SHA-256, bytes, MIME type, and ASCII-safe filename. The server streams only the requested allowlisted item after rechecking its regular-file boundary, real path, bytes, and hash; the UI pins every action to the displayed immutable run and keeps paths/hashes inside a collapsed Technical details disclosure.
- Files touched: `src/traffic_sim/portfolio_release.py`; `schemas/portfolio-route-manifest.schema.json`; `portfolio.sources.json`; `src/components/dossier/portfolioRelease.ts`; `src/components/dossier/types.ts`; `src/app/api/downloads/[artifactId]/route.ts`; `src/components/dossier/DownloadActions.tsx`; dossier page; Python/TypeScript/browser contract tests; `.omx/evidence/portfolio-m2-ultraqa.md`.
- Verification: promoted `abay-20260814T173900Z-m2downloads` with 11 primary artifacts and 5 downloads; `--verify-current` and `--verify-sources` passed; 106 Python tests; manifest/frontend/download/English contracts; lint/typecheck/build; production smoke confirmed five 200 attachments with MIME/filename/`nosniff`/run/source/hash headers, unknown download 404, unsafe run 400, and production mutation POST 404.
- Generated artifact: immutable M2 portfolio run and adversarial QA report at `.omx/evidence/portfolio-m2-ultraqa.md`.
- Unresolved risks: no claim levels changed; browser print remains the v0.1 PDF route; dependency security, responsive/a11y QA, CI/container proof, and owner-governed release material remain later milestones.
- Claim labels changed: none. The dossier/KPIs remain `proxy`; package/workflow remain `demo`; road geometry remains a non-live `real-data` snapshot.
- Next action: complete M3 accessibility, responsive, visual, metadata, privacy, and print QA without weakening the new release-bound download contract.

### 2026-08-14 - M3 Accessibility, Privacy, and Portfolio Metadata Gate

- What changed: added focusable main targets, table caption and map alternative, WCAG contrast corrections, a client-only lazy dossier-map boundary, CARTO privacy disclosure, print styling, dossier canonical metadata, generated Open Graph image, no-index robots policy, structured project metadata, and repeatable axe/responsive/privacy/three-browser/print QA. Added tracked Lighthouse CI configuration with exact package and image-digest pins.
- Files touched: dossier page/components; `src/app/robots.ts`; `src/app/scenarios/abay-signal-retiming/dossier/opengraph-image.tsx`; `lighthouserc.cjs`; `security-tools.lock.json`; `tests/portfolio_m3_quality.mjs`; `.omx/evidence/portfolio-m3-ultraqa.md`.
- Verification: zero serious/critical axe on dossier and sandbox; four responsive widths; Chromium/Firefox/WebKit; no dossier cookies/storage/external requests; CARTO-only sandbox requests; metadata, print and PDF checks; lint, TypeScript, production build, English/download contracts and diff check passed.
- Generated artifacts: `reports/qa/m3-browser-quality.json` plus the six hashed visual/print samples in `.omx/evidence/portfolio-m3-ultraqa.md`.
- Unresolved risks: PERF-02 remains pending because the local Docker daemon is unavailable; five Lighthouse runs must execute only in the digest-pinned CI container. Existing Deck.gl loader-chain audit findings are M4 work.
- Claim labels changed: none. Dossier/KPIs remain `proxy`, workflow/package remain `demo`, and road geometry remains a non-live `real-data` snapshot.
- Next action: remove the vulnerable sandbox map-loader chain and run the pinned-container Lighthouse collection as part of M4/M5; do not relax no-index until the owner approves a public host.

### 2026-08-15 - Stitch Quiet Evidence Redesign Complete

- What changed: used Stitch project `15089572861475027317` to define and implement a restrained English portfolio system for the dossier and sandbox. The dossier now opens with the case identity, source-bound `36 s → 32 s` control, `proxy` recommendation and a compact route to evidence/downloads; the KPI ledger precedes a framed supporting map; the full workbench is a warm-paper evidence chapter instead of a dark dashboard. The sandbox preserves the map/data contract and playback behaviour while moving controls and supporting panels into a non-overlapping desktop grid and normal mobile document flow. Timestamped vehicle paths now render an interpolated fading trail through the allowed `PathLayer`; mobile controls are an accessible closed-by-default disclosure; full limitations and adjacent `demo`/`proxy` labels remain visible. Shared navigation, footer, loading, error and 404 states use the same tokens and typography.
- Files touched: `.stitch/DESIGN.md`; `.stitch/designs/quiet-evidence-dossier-desktop.html`; `.stitch/designs/quiet-evidence-dossier-mobile.html`; `src/app/globals.css`; `src/app/layout.tsx`; `src/app/loading.tsx`; `src/app/error.tsx`; `src/app/not-found.tsx`; `src/components/site/`; `src/app/scenarios/abay-signal-retiming/dossier/DossierPage.module.css`; dossier page/components; `src/app/sandbox/page.tsx`; `src/components/TrafficMap.tsx`; `src/components/TrafficMap.module.css`; `src/components/tripTrail.mjs`; `tests/trip_trail_animation.mjs`; `tests/portfolio_m3_quality.mjs`; `scripts/verify-public-routes.sh`; `docs/assets/abay-dossier-portfolio.png`; current release and evidence records.
- Verification: English/download/frontend/docs and trip-trail contracts passed; lint, TypeScript and Next 16.3.0 production build passed; source slice passed 35/35 with 13 hashes; `--verify-current` passed for `abay-20260815T053423Z-cf0d2671a3` with 11 route artifacts and 43 aliases; `PORTFOLIO_TEST_PORT=3042 npm run verify:public-routes` passed. Fresh visible-browser QA confirmed one H1/main, no Cyrillic, no overflow at 390/768/1280/1440, no sandbox panel intersections, no page/console errors, zero Axe violations on both routes, 44 px mobile application targets, closed-by-default mobile controls, and all five screenshots captured.
- Generated artifacts: Stitch desktop/mobile reference exports under `.stitch/designs/`; current QA report `reports/qa/m3-browser-quality.json` with SHA-256 `57ca3ae4a2e9b62b5154100c80576c01a524132bfe6ca5002570ec05d05f0239`; refreshed `reports/ui/m3-*`; canonical 1440×900 screenshot `docs/assets/abay-dossier-portfolio.png` with SHA-256 `5838b1e4ab72ad12bbe09535462ad2fe29ef1bd2101067ea254e7e24dccc3fcb`; promoted immutable run `abay-20260815T053423Z-cf0d2671a3`.
- Unresolved risks: the interface is portfolio-ready, but the evidence is still not calibrated or procurement-ready. Observed traffic/bus data, empirical validation, sourced CAPEX/OPEX, authenticated decision custody, pinned-container Lighthouse evidence, licence/citation decisions and clean tagged release governance remain open.
- Claim labels changed: none. Dossier/KPIs remain `proxy`; workflow/package remain `demo`; road geometry remains a non-live `real-data` snapshot.
- Next action: run the owner-governed release/security track separately; for evidence quality, attach observed Abay counts, travel times, current signal timing, bus reliability and sourced costs before considering any claim upgrade.
