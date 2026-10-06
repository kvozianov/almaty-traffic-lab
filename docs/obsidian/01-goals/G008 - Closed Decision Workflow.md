---
title: G008 - Closed Decision Workflow
project: Almaty Mobility Decision Platform
type: ultragoal-function
goal_id: G008
goal_title: Closed Decision Workflow
goal_status: completed
product_status: implemented
priority: P2
owner: Shared
first_epic: false
claim_level: demo
depends_on:
  - G002
  - G005
next_action: Add dossier lifecycle, accountability, evidence-freeze, and permission rules to support the Evidence-Gated Decision Workbench.
acceptance_gate: One scenario moves through draft, reviewed, approved, assigned, deployed, monitored, and audited with evidence history.
tags:
  - almaty/goal
  - ai-agent/workbench
aliases:
  - G008 Decision Workflow
---

# G008 - Closed Decision Workflow

## Council Verdict

The workflow should be evidence capture, not decorative Kanban. It turns the product into a city memory system.

## Implementation Move

Create a minimal state machine:

`draft -> reviewed -> approved -> assigned -> deployed -> monitored -> audited`

Each transition should store:

- owner
- timestamp
- evidence path
- comments
- next action
- forecast-vs-fact comparison when available

## UI Architecture Addendum

Council source: [[LLM Council - UI Architecture Decision Workbench]].

The workbench needs an explicit dossier custody model before UI polish. The decision buttons are not enough; the UI must show who owns, reviews, freezes, disputes, and supersedes evidence.

Recommended lifecycle for the first Abay dossier flow:

`draft -> run_created -> dossier_generated -> evidence_frozen -> engineering_reviewed -> procurement_checked -> decision_recorded -> exported -> superseded`

Each state should expose:

- owner
- reviewer
- timestamp
- scenario version
- input hash
- output hash
- claim level
- data freshness
- limitations
- missing evidence

Open governance questions:

- Who can create a run?
- Who can freeze a dossier?
- Who can downgrade a claim?
- Who can attach counter-evidence?
- What happens when engineering and procurement disagree?
- How does stale KPI JSON block export?

## Files To Touch First

- `src/traffic_sim/workflow.py`
- `src/traffic_sim/web_app.py`
- `src/app/api/workflow/route.ts`
- `data/workflows/`
- dossier templates

## Acceptance Gate

One scenario can move from draft to post-audit with decision history and comparison evidence.

## Avoid

- Generic status labels with no required evidence.
- Approval states that do not lock artifact versions.
- Workflow before the dossier artifact exists.

## Evidence Links

- [[G002 - Scenario Dossier MVP]]
- [[G005 - Data Trust And Audit Layer]]
- [[Artifact Registry]]
- `src/traffic_sim/workflow.py`
- `scripts/generate_decision_workflow.py`
- `reports/workflows/abay-signal-retiming-decision-workflow.json`
- `reports/workflows/abay-signal-retiming-decision-workflow-engineer-tasks.csv`
- `reports/workflows/abay-signal-retiming-decision-workflow-monitoring.json`
- `reports/workflows/abay-signal-retiming-decision-workflow-post-audit.json`
- `src/app/api/workflow/route.ts`

## Agent Handoff

### 2026-08-15 Fresh Adversarial Workflow QA

- What changed: exercised the complete seven-state workflow, artifact locks, current promoted hashes, negative transitions, malformed/tampered evidence, path traversal/symlink cases, Unicode/injection-like inert data and concurrent writers in isolated temporary roots. No workflow behavior was changed.
- Files touched: `.omx/evidence/portfolio-fresh-end-to-end-qa-20260815.md`; `docs/obsidian/01-goals/G008 - Closed Decision Workflow.md`; `docs/obsidian/01-goals/G002 - Scenario Dossier MVP.md`; `docs/obsidian/03-registries/Artifact Registry.md`.
- Verification: workflow/context tests 5/5; full `draft → reviewed → approved → assigned → deployed → monitored → audited`; 7/7 history hashes and 5/5 locks; 12 concurrent CLI and 12 concurrent API calls returned parseable artifacts; promoted alias/immutable workflow files match the manifest now.
- Unresolved risks: directories can satisfy evidence without a hash; later tampering does not recalculate completeness; GET mutates workflow artifacts; in-root symlink escape is followed; one procurement task names a nonexistent status; endpoints have no auth, production gate, strict body/path validation, atomic/append-only custody or human approval semantics.
- Claim labels changed: none. This remains a `demo` evidence-artifact generator, not an authenticated, signed or field-connected municipal workflow.
- Next action: make GET read-only and production writes unavailable, require canonical regular-file evidence with ongoing hash verification, then add authenticated actors, valid state contracts and atomic/append-only custody before any deployment claim.

### 2026-06-05 Checkpoint

- What changed: implemented a file-based closed decision workflow from the Abay signal-retiming dossier. The state machine moves through `draft -> reviewed -> approved -> assigned -> deployed -> monitored -> audited`, stores owner/timestamp/evidence path/hash/comments/next action for every transition, locks dossier artifact hashes, exports engineer tasks, creates a monitoring plan, and attaches forecast-vs-fact post-audit evidence with a recalibration flag.
- Files touched: `src/traffic_sim/workflow.py`, `scripts/generate_decision_workflow.py`, `tests/test_workflow.py`, `src/app/api/workflow/route.ts`, `src/traffic_sim/web_app.py`, `docs/analytics_contract.md`, `reports/workflows/abay-signal-retiming-decision-workflow.json`, `reports/workflows/abay-signal-retiming-decision-workflow-engineer-tasks.csv`, `reports/workflows/abay-signal-retiming-decision-workflow-monitoring.json`, `reports/workflows/abay-signal-retiming-decision-workflow-post-audit.json`, `docs/obsidian/01-goals/G008 - Closed Decision Workflow.md`, `docs/obsidian/03-registries/Artifact Registry.md`, `docs/obsidian/03-registries/Claim Ledger.md`, `docs/obsidian/03-registries/First Corridor Pack - Abay.md`, `docs/obsidian/00-command-center/First Epic Execution Plan.md`.
- Verification: `PYTHONPATH=src python3 -m compileall -q src/traffic_sim scripts` passed; `PYTHONPATH=src python3 -m unittest tests.test_workflow` passed; `PYTHONPATH=src python3 scripts/generate_decision_workflow.py --dossier reports/dossiers/abay-signal-retiming/dossier.json --out reports/workflows` generated workflow/task/monitoring/audit artifacts; JSON validation passed for workflow, monitoring, and post-audit artifacts; assertion harness proved the full status path, evidence completeness, task IDs, artifact locks, and forecast-vs-fact audit items; `npm run lint` passed; `npm run build` passed and listed `/api/workflow`; live GET/POST smoke on `http://localhost:3013/api/workflow` returned audited workflow; in-app Browser opened the route.
- Claim labels changed: closed decision workflow moved from not implemented to `demo`; underlying dossier/KPI claims remain `proxy`.
- Unresolved risks: workflow users are string owners, not authenticated accounts; approvals are evidence records, not legal signatures; deployed/monitored states are demo records until connected to field work orders and observed feeds; forecast-vs-fact values are demonstrator observed values and must be replaced with measured outcomes.
- Next action: proceed to [[G009 - Enterprise And Procurement Readiness]] to document roles, audit log, scenario versioning, local deployment, data residency, acceptance checklist, and TCO using this workflow evidence.

### 2026-06-06 UI Architecture Council Plan

- What changed: added a custody/lifecycle model required for the Evidence-Gated Decision Workbench. This keeps [[G002 - Scenario Dossier MVP]] from becoming only a screen export and ties UI decisions to auditable ownership.
- Files touched: `docs/obsidian/02-council/LLM Council - UI Architecture Decision Workbench.md`, `docs/obsidian/01-goals/G002 - Scenario Dossier MVP.md`, `docs/obsidian/01-goals/G008 - Closed Decision Workflow.md`, `docs/obsidian/00-command-center/Almaty Mobility Command Center.md`.
- Verification: documentation-only update; no generated artifacts; no code behavior changed.
- Unresolved risks: no authenticated users, no legal signature policy, no append-only audit store, no stale evidence blocking, no disagreement/escalation workflow.
- Claim labels changed: none. Closed decision workflow remains `demo`.
- Next action: define the first dossier state machine for `/scenarios/abay-signal-retiming/dossier` and decide which states are visible in the right-side trust/action panel.
