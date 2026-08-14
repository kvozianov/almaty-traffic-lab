---
title: AI Agent Operating Manual
project: Almaty Mobility Decision Platform
type: agent-manual
status: active
created: 2026-06-05
tags:
  - almaty/project
  - ai-agent/manual
  - ai-agent/workbench
aliases:
  - Agent Manual
  - Almaty Agent Manual
---

# AI Agent Operating Manual

## Start Sequence

1. Open [[Almaty Mobility Command Center]].
2. Check [[Almaty Goals.base]] for the next P0/P1 goal.
3. Read the specific goal note before touching code.
4. Check [[Artifact Registry]] for expected outputs and evidence files.
5. Check [[Claim Ledger]] before making buyer-facing claims.
6. If implementing, update code and evidence. If planning, update the relevant `.md` goal note.

## Non-Negotiable Rule

The product is not "a traffic dashboard." The product is a defensible municipal decision artifact:

`scenario config -> run metadata -> KPI JSON -> dossier -> audit/procurement evidence`

The dashboard supports that chain. It is not the source of truth.

## Claim Labels

Use these labels in notes, reports, UI copy, and dossier text:

| Label | Meaning |
|---|---|
| `demo` | Visual or workflow demonstration; not evidence for a real decision. |
| `proxy` | Transparent simplified formula or placeholder until real data/model exists. |
| `calibrated` | Compared against local calibration/validation data with visible error. |
| `real-data` | Imported from a real source with provenance, freshness, and legal status. |
| `procurement-ready` | Has acceptance evidence, limitations, reproducibility, and buyer-safe wording. |

Never silently upgrade a claim level. Add evidence first.

## Agent Handoff Format

When leaving work for another AI agent, update the relevant goal note with:

- `next_action`
- touched files
- verification command or artifact
- unresolved risks
- claim labels changed
- evidence links

Use the "Agent Handoff" section in each G001-G012 note.

## Allowed Editing Pattern

- Code changes belong in the normal project files.
- Strategy, audit, acceptance, and evidence links belong in `docs/obsidian`.
- Durable plan source remains `.omx/ultragoal/goals.json`.
- Do not replace `.omx/ultragoal` with Obsidian notes. Obsidian explains and operates the plan.

## Buyer-Facing Acceptance Loop

Every first-epic feature must support this loop:

1. Select one corridor and one proposed measure.
2. Run baseline vs measure.
3. Generate dossier and executive KPI summary.
4. Review objections: data trust, cost, risk, legal/source limitations.
5. Decide: fund, defer, reject, or request more evidence.
6. Save the decision trail.

If a feature cannot participate in this loop, it is not P0 for the first epic.

## Routing Between Jules And Codex

Current project split from [[TASKS]]:

| Area | Owner |
|---|---|
| Python simulation, algorithms, datasets, backend model logic | Jules |
| React dashboard, MapLibre/deck.gl visuals, UI, export controls | Codex |
| JSON contracts, dossier schema, run metadata, acceptance evidence | Shared |

Agents should respect this boundary unless the task explicitly requires crossing it.
