# Almaty Mobility Decision Platform Design System

## Product Position

This project presents an evidence-gated municipal decision dossier, not a marketing site and not a map-first dashboard.

Primary chain:

`scenario config -> run metadata -> KPI JSON -> scenario dossier -> audit/procurement evidence -> pilot monitoring / forecast-vs-fact`

## Audience

- Executive sponsor
- Transport planner
- Traffic engineer
- Data steward
- Procurement analyst

## Tone

- Institutional
- Dense but readable
- Audit-forward
- Procurement-facing
- Calm, serious, and explicit about evidence gaps

## UI Rules

- The dossier and evidence chain are the primary product surface.
- The map is supporting evidence only.
- Keep claim badges visible near decisions, KPIs, sources, workflow, and export records.
- Do not show an unconditional fund action while the dossier claim level is `proxy`.
- Show missing evidence and next action near every stronger decision surface.
- Prefer compact tables, ledgers, passports, and panels over decorative hero sections.
- Use dark institutional surfaces with clear borders and restrained contrast.
- Keep panels stable and scannable; no decorative orbs, marketing gradients, or oversized hero copy.

## Claim Language

Allowed labels:

- `demo`
- `proxy`
- `calibrated`
- `real-data`
- `procurement-ready`

Do not upgrade labels without evidence in `docs/obsidian/03-registries/Claim Ledger.md`.

Safe buyer position:

The prototype can generate a reproducible proxy-level Abay Scenario Dossier with run metadata, KPI deltas, source labels, limitations, workflow evidence, and procurement checklist artifacts.
