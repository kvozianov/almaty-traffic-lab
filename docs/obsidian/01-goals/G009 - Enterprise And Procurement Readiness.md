---
title: G009 - Enterprise And Procurement Readiness
project: Almaty Mobility Decision Platform
type: ultragoal-function
goal_id: G009
goal_title: Enterprise And Procurement Readiness
goal_status: completed
product_status: implemented
priority: P2
owner: Shared
first_epic: false
claim_level: demo
depends_on:
  - G002
  - G005
  - G012
next_action: Replace demo procurement gaps with authenticated roles, signed approval policy, security review, deployment scan, and sourced TCO evidence.
acceptance_gate: Tender checklist covers deployment, roles, audit log, data residency, SLA/security, training, acceptance, and TCO with linked evidence.
tags:
  - almaty/goal
  - ai-agent/workbench
aliases:
  - G009 Procurement Readiness
---

# G009 - Enterprise And Procurement Readiness

## Council Verdict

Municipal buying requires governance, deployment, support, and acceptance evidence. Do not say "enterprise later" if the pitch needs procurement confidence.

## Implementation Move

Create a procurement packet:

- roles and responsibility model
- audit log and scenario versioning story
- on-prem/Docker deployment path
- Kazakhstan data residency notes
- backups and data handling
- SLA/security posture
- training and acceptance checklist
- 3-year TCO framing

## Files To Touch First

- `docs/procurement_readiness.md`
- `docs/data_sources.md`
- `README_METHODS.md`
- `docker-compose.yml`
- run metadata/audit helpers

## Acceptance Gate

A tender checklist maps each buyer requirement to implemented/prototype/planned evidence.

## Avoid

- Full auth/roles build before proof is needed.
- Security claims without deployment evidence.
- Procurement language unsupported by [[Artifact Registry]].

## Evidence Links

- [[G002 - Scenario Dossier MVP]]
- [[G005 - Data Trust And Audit Layer]]
- [[G012 - Reproducibility And Deployment]]
- [[Claim Ledger]]
- `docs/procurement_readiness.md`
- `docs/data_sources.md`
- `README_METHODS.md`
- `Dockerfile`
- `docker-compose.yml`
- `reports/procurement/tender_checklist.json`
- `reports/procurement/tender_checklist.csv`

## Agent Handoff

### 2026-06-05 Checkpoint

- What changed: created a demo-level procurement packet with a tender checklist mapped to evidence and gaps, procurement readiness documentation, data-source/legal posture documentation, a methods/local runbook, and a Docker/Compose prototype path. The checklist covers roles, audit log, scenario versioning, on-prem run path, Kazakhstan data residency, backups/retention, SLA/security posture, training/acceptance, and 3-year TCO framing.
- Files touched: `src/traffic_sim/procurement.py`, `scripts/generate_procurement_packet.py`, `tests/test_procurement.py`, `docs/procurement_readiness.md`, `docs/data_sources.md`, `README_METHODS.md`, `Dockerfile`, `.dockerignore`, `docker-compose.yml`, `reports/procurement/tender_checklist.json`, `reports/procurement/tender_checklist.csv`, `docs/obsidian/01-goals/G009 - Enterprise And Procurement Readiness.md`, `docs/obsidian/03-registries/Artifact Registry.md`, `docs/obsidian/03-registries/Claim Ledger.md`, `docs/obsidian/03-registries/First Corridor Pack - Abay.md`, `docs/obsidian/00-command-center/First Epic Execution Plan.md`.
- Verification: `PYTHONPATH=src python3 -m compileall -q src/traffic_sim scripts` passed; `PYTHONPATH=src python3 -m unittest tests.test_procurement` passed; `PYTHONPATH=src python3 scripts/generate_procurement_packet.py --out reports/procurement` generated JSON/CSV checklist artifacts; `python3 -m json.tool reports/procurement/tender_checklist.json` passed; assertion harness proved nine required tender areas and local/on-prem run commands; `docker-compose.yml` parsed with PyYAML and includes the `app` service and `3000:3000` port; `npm run lint` passed; `npm run build` passed.
- Blocked verification: `docker compose config` could not run because `docker` is not installed in this shell (`zsh:1: command not found: docker`).
- Claim labels changed: procurement readiness packet moved from not implemented to `demo`. No enterprise, production SLA, security certification, legal signature, or procurement-ready claim was added.
- Unresolved risks: roles are documented but not authenticated; audit is file-based, not append-only signed storage; Docker path is not built/scanned in this environment; TCO is category framing only; Kazakhstan residency posture needs legal/hosting evidence; G012 reproducibility/deployment remains pending.
- Next action: proceed to [[G010 - Real Data Integrations]] or [[G012 - Reproducibility And Deployment]] to replace procurement gaps with stronger technical evidence.
