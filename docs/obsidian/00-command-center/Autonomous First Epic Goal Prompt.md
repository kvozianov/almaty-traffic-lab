---
title: Autonomous First Epic Goal Prompt
project: Almaty Mobility Decision Platform
type: goal-prompt
status: ready
created: 2026-06-05
tags:
  - almaty/project
  - ai-agent/workbench
  - ai-agent/goal-prompt
aliases:
  - First Epic Goal Prompt
  - Autonomous G001-G005-G004-G002 Prompt
---

# Autonomous First Epic Goal Prompt

Use this prompt when starting an AI agent goal for the first sellable epic.

## Prompt To Use

```text
Goal: Execute the first sellable epic for the Almaty Mobility Decision Platform by following AGENTS.md and the Obsidian workbench.

You are working in:
/Users/kirill/Documents/code/PROJECTS/project 1 - city traffic

Before implementation, read:
1. AGENTS.md
2. docs/obsidian/00-command-center/Almaty Mobility Command Center.md
3. docs/obsidian/00-command-center/AI Agent Operating Manual.md
4. docs/obsidian/00-command-center/Obsidian Vault Contract.md
5. docs/obsidian/02-council/LLM Council - Implementation Audit.md
6. docs/obsidian/03-registries/Artifact Registry.md
7. docs/obsidian/03-registries/Claim Ledger.md
8. docs/obsidian/03-registries/First Corridor Pack - Abay.md

Do not rely on memory. First create or update this note:
docs/obsidian/00-command-center/First Epic Execution Plan.md

In that note, record:
- the exact goal in your own words
- the implementation sequence
- acceptance gates for each stage
- files you expect to touch
- verification commands/artifacts
- checkpoint rules
- current risks
- handoff format for the next agent

Then execute the work in this order:

Stage 1: G001 - Baseline MVP Inventory
- Read docs/obsidian/01-goals/G001 - Baseline MVP Inventory.md
- Create/update baseline inventory and screenshot/API evidence manifest.
- Verify what is implemented, partial, stub, or derived.
- Update G001 Agent Handoff and Artifact Registry.

Stage 2: G005 - Data Trust And Audit Layer
- Read docs/obsidian/01-goals/G005 - Data Trust And Audit Layer.md
- Implement the minimal RunPassport/run metadata path needed for dossiers.
- Include seed, git hash, data sources, scenario params, calibration/validation notes, limitations, and claim labels.
- Update G005 Agent Handoff, Artifact Registry, and Claim Ledger if claim levels change.

Stage 3: G004 - Executive KPI Layer
- Read docs/obsidian/01-goals/G004 - Executive KPI Layer.md
- Implement transparent executive KPI proxies needed for the first dossier: person-hours, speed delta, queue/load proxy, bus reliability proxy if feasible, emissions proxy if feasible, CAPEX/OPEX placeholders, ROI/payback proxy, confidence/claim level.
- Update analytics contract or implementation notes as needed.
- Update G004 Agent Handoff and Artifact Registry.

Stage 4: G002 - Scenario Dossier MVP
- Read docs/obsidian/01-goals/G002 - Scenario Dossier MVP.md
- Use docs/obsidian/03-registries/First Corridor Pack - Abay.md as the first corridor anchor.
- Implement a first dossier path using the product spine:
  scenario config -> run metadata -> KPI JSON -> scenario dossier -> audit/procurement evidence
- Generate the first Abay baseline-vs-measure dossier artifact if feasible.
- The dossier must include baseline, proposed measure, KPI deltas, assumptions, sources, risks, CAPEX/OPEX placeholders, trust metadata, limitations, and a buyer decision recommendation: fund, defer, reject, or request more evidence.
- Update G002 Agent Handoff, Artifact Registry, and Claim Ledger.

Rules:
- Do not jump to G003-G012 until G002 acceptance_gate is either met or clearly blocked with evidence.
- Do not build broad platform features, public narrative mode, decision knowledge graph, partner APIs, or full operational mode unless needed for the first dossier.
- Do not silently upgrade claim levels. Use demo/proxy/calibrated/real-data/procurement-ready exactly as defined in Claim Ledger.
- Do not leave progress only in chat. After every stage, write a checkpoint in First Epic Execution Plan.md and in the relevant G00X note.
- If context gets compressed or the session is interrupted, the next agent must be able to continue from Obsidian alone.

Verification:
- Run targeted tests/checks for changed code.
- Validate any edited .base files as YAML and .canvas files as JSON.
- If app-level verification is needed, run build/lint/tests where feasible and record failures honestly.
- Record all verification commands and results in Obsidian handoff sections.

Completion condition:
The goal is complete only when G001, G005, G004, and G002 have updated Obsidian handoffs, artifact/evidence links, and the first Scenario Dossier path is either working or has a precise blocker with next action.
```

## Recommended Use

Use this as a Codex goal or as the first message in a long-running agent thread.

The prompt intentionally limits scope to the first sellable epic:

`G001 -> G005 -> G004 -> G002`

This is safer than asking for all `G001-G012` in one pass.
