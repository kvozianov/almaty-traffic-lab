---
title: Obsidian Vault Contract
project: Almaty Mobility Decision Platform
type: vault-contract
status: active
created: 2026-06-05
tags:
  - almaty/project
  - obsidian/contract
  - ai-agent/workbench
aliases:
  - Vault Contract
---

# Obsidian Vault Contract

This contract keeps the vault usable by humans and AI agents.

## Folder Map

| Folder | Purpose |
|---|---|
| `docs/obsidian/00-command-center` | Start here, operating rules, global context. |
| `docs/obsidian/01-goals` | One note per durable G001-G012 function. |
| `docs/obsidian/02-council` | LLM Council source notes and synthesis. |
| `docs/obsidian/03-registries` | Artifact registry, claim ledger, corridor packs. |
| `docs/obsidian/04-templates` | Reusable note templates. |
| `docs/obsidian/05-bases` | Obsidian Bases for filtering work. |

## Required Goal Frontmatter

Each goal note must include:

```yaml
goal_id: G002
goal_title: Scenario Dossier MVP
goal_status: planned
product_status: not_implemented
priority: P0
owner: Shared
first_epic: true
claim_level: demo
depends_on:
  - G001
  - G004
  - G005
next_action: Define dossier schema and first Abay scenario.
acceptance_gate: One Abay dossier exports with KPIs, metadata, risks, and cost placeholders.
```

## Required Goal Sections

Every G001-G012 note should keep these headings:

- Council Verdict
- Implementation Move
- Files To Touch First
- Acceptance Gate
- Avoid
- Evidence Links
- Agent Handoff

## Wikilink Rules

- Use `[[wikilinks]]` for Obsidian notes.
- Use inline code for code paths, for example `src/traffic_sim/analytics.py`.
- Link every high-level claim to either a goal note, registry note, artifact, or source file.

## Evidence Rules

Evidence can be:

- passing command output summarized in a note
- generated JSON/CSV/PDF/HTML path
- screenshot manifest entry
- API route response contract
- validation table
- run metadata

Evidence should be linked from the goal note and listed in [[Artifact Registry]].

## Bases

Use these views:

- [[Almaty Goals.base]]
- [[Almaty Council.base]]
- [[Almaty Registries.base]]
- [[Almaty Agent Workbench.base]]

If a note does not appear in a Base, its tags or frontmatter are probably wrong.
