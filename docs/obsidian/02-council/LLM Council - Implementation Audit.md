---
title: LLM Council - Implementation Audit
project: Almaty Mobility Decision Platform
type: council-synthesis
status: active
created: 2026-06-05
tags:
  - almaty/council
  - ai-agent/audit
  - ultragoal
aliases:
  - Council Implementation Audit
  - G001-G012 Council Synthesis
---

# LLM Council - Implementation Audit

Question sent to the council:

> How should each G001-G012 function be implemented, audited, and structured in Obsidian so AI agents can work from it effectively, with Scenario Dossier MVP as the first sellable akimat epic?

Source council notes:

- [[First Principles Goal Audit]]
- [[Almaty Mobility Executor Audit]]
- [[LLM Council Outsider Goal Audit]]
- [[LLM Council - Source Transcript]]

Two additional advisor outputs were captured in-session:

- Contrarian: product spine, trust risks, overclaiming warnings.
- Expansionist: dossier as core SKU, corridor evidence packs, long-term platform upside.

## Where The Council Agrees

- [[G002 - Scenario Dossier MVP]] is the anchor epic.
- [[G001 - Baseline MVP Inventory]], [[G004 - Executive KPI Layer]], [[G005 - Data Trust And Audit Layer]], and [[G012 - Reproducibility And Deployment]] must support G002 before broad expansion.
- The system should be schema-first: scenario, portfolio, KPI, dossier, run passport, workflow.
- Claims must be labeled as `demo`, `proxy`, `calibrated`, `real-data`, or `procurement-ready`.
- One credible corridor pack beats a broad but thin platform story.

## Where The Council Clashes

The Expansionist wants to productize the broader platform quickly: public narrative mode, partner APIs, control-room product, decision knowledge graph.

The Contrarian and reviewers warn that this can bury the first SKU. Their sharper recommendation is:

> Prove one corridor dossier can support a municipal funding/defer/reject decision before building platform breadth.

Resolution: keep expansion ideas in the roadmap, but do not treat them as first-month implementation unless they directly improve the first dossier.

## Blind Spots The Council Caught

The original five advisor answers were strong on strategy and implementation, but weak on the actual Obsidian operating model.

The final system therefore needs:

- strict goal note templates
- frontmatter fields for Bases
- artifact registry
- claim ledger
- agent handoff fields
- acceptance gates per goal
- buyer-facing decision ceremony
- corridor-specific demo script
- review checklist for claims and evidence

## The Recommendation

Build the Obsidian layer as an agent workbench around a single first-epic workflow:

`Abay corridor pack -> scenario config -> baseline/measure run -> executive KPI block -> run passport -> dossier export -> buyer decision`

Then implement code in this order:

1. [[G001 - Baseline MVP Inventory]]
2. [[G005 - Data Trust And Audit Layer]]
3. [[G004 - Executive KPI Layer]]
4. [[G002 - Scenario Dossier MVP]]
5. [[G003 - ScenarioPortfolio And Batch Runner]]
6. [[G006 - Municipal Scenario Library]]
7. [[G012 - Reproducibility And Deployment]]

The other goals remain valuable, but should wait until the first dossier is defensible.

## One Thing To Do First

Complete [[First Corridor Pack - Abay]] and use it as the forcing function for G001/G004/G005/G002.

Do not choose another broad platform feature until the Abay dossier can answer:

- What changed?
- Who benefits?
- What does it cost?
- What are the risks?
- Why should akimat trust the numbers?
- What decision should leadership make next?
