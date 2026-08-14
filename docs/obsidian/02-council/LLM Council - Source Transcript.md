---
title: LLM Council - Source Transcript
project: Almaty Mobility Decision Platform
type: council-transcript
status: active
created: 2026-06-05
tags:
  - almaty/council
  - ai-agent/audit
  - ultragoal
aliases:
  - Council Source Transcript
---

# LLM Council - Source Transcript

## Framed Question

How should each G001-G012 function be implemented, audited, and structured in Obsidian so AI agents can work from it effectively, with [[G002 - Scenario Dossier MVP]] as the first sellable akimat epic?

## Advisor Responses

### Response A - First Principles

Stored in [[First Principles Goal Audit]].

Key signal: build the municipal decision artifact first; evidence travels with every output; schemas before screens; narrow to 1-2 corridors before city-wide breadth.

### Response B - Contrarian

#### G001 Baseline MVP Inventory

- Biggest risk: inventory becomes a doc dump instead of a runnable baseline.
- Best move: define one canonical baseline scenario with fixed inputs, CLI/API entrypoint, seed, outputs, screenshots, and KPI JSON.
- Avoid: auditing every file before proving one complete workflow.
- Acceptance signal: fresh clone can run baseline and produce the same dossier/KPI artifacts.

#### G002 Scenario Dossier MVP

- Biggest risk: dossier looks polished but cannot justify its numbers.
- Best move: build the dossier around traceable assumptions, scenario deltas, KPI tables, map snapshots, and explicit decision implication blocks.
- Avoid: narrative-only reports, vague improvement language, or unlinked charts.
- Acceptance signal: a non-technical municipal reviewer can answer what changed, who benefits, what it costs, and why to trust it.

#### G003 ScenarioPortfolio And Batch Runner

- Biggest risk: batch runner becomes slow, flaky, and opaque.
- Best move: treat each scenario as versioned config plus deterministic run metadata, with resumable execution and per-run artifacts.
- Avoid: hidden defaults, ad hoc Python scripts, or frontend-only scenario state.
- Acceptance signal: ten scenarios can run unattended and produce comparable KPI outputs.

#### G004 Executive KPI Layer

- Biggest risk: KPIs are too academic or too many to support procurement decisions.
- Best move: limit to decision-grade KPIs: delay, throughput, emissions proxy, public transport impact, geography/equity, cost proxy, confidence.
- Avoid: metric dashboards without thresholds, interpretation, or tradeoff framing.
- Acceptance signal: each KPI has formula, source, unit, owner, and good/bad interpretation.

#### G005 Data Trust And Audit Layer

- Biggest risk: trust layer is bolted on after the model is already unexplainable.
- Best move: add provenance, assumptions, validation status, config hash, data freshness, and uncertainty notes to every generated artifact.
- Avoid: AI-generated recommendation without audit trail.
- Acceptance signal: any dossier number can be traced back to input config, model version, and source assumptions.

#### G006 Municipal Scenario Library

- Biggest risk: library becomes a generic template gallery, not Almaty-specific.
- Best move: encode real municipal questions: BRT corridor, signal timing, bus priority, school-zone safety, parking restriction, lane reallocation, construction detour.
- Avoid: abstract demo scenarios with no recognizable policy buyer.
- Acceptance signal: each library scenario maps to a real department use case and required decision.

#### G007 Operational Mode And Recommendations

- Biggest risk: recommendations overclaim authority and create political/procurement risk.
- Best move: generate ranked options with constraints, confidence, tradeoffs, and requires-human-validation wording.
- Avoid: autopilot-style prescriptions.
- Acceptance signal: recommendation output shows options, rationale, risks, and missing data before action.

#### G008 Closed Decision Workflow

- Biggest risk: workflow becomes decorative status tracking instead of evidence capture.
- Best move: model municipal lifecycle: request, scenario setup, review, revision, approval, procurement package, archive.
- Avoid: generic Kanban with no accountability or artifact locking.
- Acceptance signal: a scenario can move from request to approved dossier with comments, versions, and signoff history.

#### G009 Enterprise And Procurement Readiness

- Biggest risk: product demos well but fails buyer due diligence.
- Best move: prepare security posture, deployment model, admin roles, audit logs, SLA assumptions, data handling, export formats, and procurement narrative.
- Avoid: "enterprise later" as the only answer.
- Acceptance signal: procurement packet covers architecture, risks, support model, compliance notes, and sample deliverables.

#### G010 Real Data Integrations

- Biggest risk: real data becomes the first blocker and stalls the whole platform.
- Best move: build adapters with synthetic/fallback data first, then plug in GIS, GTFS, sensors, counts, crash data, and municipal feeds incrementally.
- Avoid: hard-coding Almaty data sources before contracts/access are known.
- Acceptance signal: each data source has adapter, schema contract, freshness marker, and degraded-mode behavior.

#### G011 Research Metrics And Publication Visuals

- Biggest risk: research visuals distract from municipal buying needs.
- Best move: separate publication mode from decision mode while sharing the same validated KPI outputs.
- Avoid: beautiful charts that cannot be exported, cited, or reproduced.
- Acceptance signal: same run can produce executive dossier visuals and paper-ready figures from identical artifacts.

#### G012 Reproducibility And Deployment

- Biggest risk: platform only works on the original developer machine.
- Best move: lock environment, seeds, configs, data fixtures, artifact paths, CI smoke tests, and one documented deployment target.
- Avoid: manual setup hidden in memory or notebooks.
- Acceptance signal: CI or clean machine can run baseline scenario and verify expected outputs.

Contrarian warnings:

1. Do not build dashboard breadth before locking the artifact contract.
2. Keep Almaty-specific defaults portable, not hard-coded.
3. Do not overpromise simulation accuracy.
4. Do not split frontend/API/Python contracts informally.
5. Do not treat [[G002 - Scenario Dossier MVP]] as report generation only.

### Response C - Executor

Stored in [[Almaty Mobility Executor Audit]].

Key signal: named files, scripts, API routes, verification commands, and first-month implementation sequence.

### Response D - Expansionist

Key signal: [[G002 - Scenario Dossier MVP]] is the core SKU.

| Goal | Hidden upside | Best implementation move | Akimat angle | Acceptance signal |
|---|---|---|---|---|
| G001 | Existing demo can be procurement proof if labeled. | Capability registry plus smoke script. | Working platform foundation, not concept deck. | Inventory note lists status, source, screenshot, API route. |
| G002 | Dossier becomes the sellable artifact. | `ScenarioDossier` JSON service, then HTML/PDF/XLSX. | Decision packet for one corridor. | Abay/Al-Farabi dossier exports with deltas, assumptions, sources, CAPEX/OPEX. |
| G003 | Capital planning engine. | Typed portfolio files and cached batch outputs. | Compare measures before construction spend. | Three scenarios run and produce ranked KPI matrix. |
| G004 | Budget language. | Shared `executive_summary` schema. | Tenge per saved hour, payback by corridor. | API, UI, dossier render same KPIs. |
| G005 | Governance feature. | Attach `RunMetadata` to every run. | Defensible procurement/public scrutiny. | Reports include lineage, calibration, confidence/error. |
| G006 | Almaty operating calendar. | Typed municipal cases. | Ready-made intervention catalog. | 10+ presets in UI and dossier exports. |
| G007 | Control-room product. | Incident in, 30/60/120 forecast out. | Operator co-pilot. | Incident returns forecast and top actions. |
| G008 | City memory system. | Simple status machine. | Scenario to signed action to post-audit. | Scenario moves through workflow and comparison. |
| G009 | Local on-prem/data residency advantage. | Procurement docs, roles/audit, Docker path. | Kazakhstan-hosted municipal platform. | Tender checklist maps requirements to evidence. |
| G010 | Adapters become moat. | Provider interfaces for OSM, GTFS, CSV, placeholders. | Connects to existing city data. | One provider import appears in UI status and metadata. |
| G011 | Technical legitimacy. | Optional research analytics pack. | International-methods annex. | KPI matrix with CIs and publication visual. |
| G012 | Procurement pilot appliance. | Config, seeds, artifacts, Docker, methods doc. | Same inputs, same dossier. | Clean machine reproduces dossier. |

Expansion opportunities:

1. Productize per-corridor Scenario Dossiers.
2. Create evidence packs for Abay, Al-Farabi, Rayymbek, Sain, Dostyk, Tole Bi.
3. Add public narrative mode later.
4. Build decision knowledge graph later.
5. Expose partner APIs later.

### Response E - Outsider

Stored in [[LLM Council Outsider Goal Audit]].

Key signal: create an outcome dictionary, artifact registry, claim labels, and a first corridor pack so officials and agents understand the same system.

## Peer Review Round

### Reviewer 1

- Strongest: Response B, because it identifies the product spine and failure modes that would kill trust.
- Biggest blind spot: Response D over-expands too early.
- Missed by all: explicit Obsidian operating system for agents, including templates, claim ledger, evidence links, acceptance gates, and bilingual dossier format.

### Reviewer 2

- Strongest: Response C, because it is most agent-operable.
- Biggest blind spot: political/procurement conversion: who signs off, what claim level is allowed, what budget/action decision it supports.
- Missed by all: Obsidian execution contract, corridor demo script, red-team checklist, sellable artifact definition.

### Reviewer 3

- Strongest: Response C, because it turns G001-G012 into buildable work.
- Biggest blind spot: Obsidian operability itself.
- Missed by all: buyer-facing acceptance loop with approve/reject/defer/request-more-evidence decision outcome.

### Reviewer 4

- Strongest: Response C, with B and E as audit overlays.
- Biggest blind spot: treating Obsidian like documentation instead of an agent workbench.
- Missed by all: the sellable akimat moment: one concrete decision ceremony.

### Reviewer 5

- Strongest: Response C.
- Biggest blind spot: Response D expands before proving the SKU.
- Missed by all: explicit note templates, stable goal IDs, artifact registry links, status fields, owner/handoff fields, acceptance tests, source freshness tags, claim labels, and a corridor-to-decision workflow.
