# Almaty Mobility Decision Platform Procurement Readiness

Status: `demo`

This packet frames what can be shown in an akimat procurement conversation today and what still needs evidence. It does not claim enterprise certification, production SLA, legal e-signature support, or procurement-ready validation.

## Buyer-Facing Position

The first sellable artifact is the Abay Scenario Dossier path:

`scenario config -> run metadata -> KPI JSON -> scenario dossier -> audit/procurement evidence`

Current strongest proof:

- Scenario Dossier: `reports/dossiers/abay-signal-retiming/dossier.md`
- Run passport: `data/runs/abay-signal-retiming-run-passport.json`
- Workflow audit: `reports/workflows/abay-signal-retiming-decision-workflow.json`
- Tender checklist: `reports/procurement/tender_checklist.json`

## Roles And Responsibilities

| Role | Responsibility | Current Evidence | Gap |
|---|---|---|---|
| Executive sponsor | Approves pilot scope and budget envelope | Workflow owner fields | No legal delegation record |
| Transport planner | Creates scenario and dossier | `reports/dossiers/abay-signal-retiming/dossier.json` | No authenticated user account |
| Traffic engineer | Reviews signal/road feasibility | `reports/workflows/abay-signal-retiming-decision-workflow-engineer-tasks.csv` | No engineering sign-off |
| Operations duty officer | Approves detours/public notices | `reports/operations/abay-major-incident-playbook.json` | No live dispatch integration |
| Data steward | Confirms source provenance and residency | `docs/data_sources.md` | No DPA or city source agreement |
| Procurement analyst | Replaces cost placeholders and checks acceptance | `reports/procurement/tender_checklist.json` | No sourced vendor quotes |
| System administrator | Runs local/on-prem app and backups | `docker-compose.yml` | No hardened production environment |

## Audit Log And Scenario Versioning

Current audit evidence is file-based:

- `RunPassport` captures seed, git hash, source fingerprints, scenario params, limitations, and claim labels.
- Workflow history captures status, owner, timestamp, evidence path, evidence hash, comments, and next action.
- Artifact Registry maps goal IDs to proof files and verification commands.

Current gaps:

- No append-only signed audit store.
- No multi-user scenario registry.
- No legal e-signature or approval delegation.

## On-Prem Deployment Story

Prototype local/on-prem path:

```bash
npm ci
PYTHONPATH=src python3 scripts/generate_dossier.py --config data/scenarios/dossier_abay_signal.json
PYTHONPATH=src python3 scripts/generate_decision_workflow.py --dossier reports/dossiers/abay-signal-retiming/dossier.json --out reports/workflows
PYTHONPATH=src python3 scripts/generate_procurement_packet.py --out reports/procurement
npm run build
docker compose config
docker compose up --build app
```

Deployment posture:

- App can run as a local Next.js service with local Python artifact generators.
- `data/` can be mounted read-only for source snapshots.
- `reports/` can be mounted read-write for generated dossiers, workflows, and procurement evidence.
- Raw municipal data should stay in city-controlled storage unless a legal agreement allows export.

## Kazakhstan Data Residency

Default procurement position:

- Host inside Kazakhstan-controlled municipal or approved local infrastructure.
- Keep raw camera, detector, Onay, Sergek, and licensed navigation data in tenant storage.
- Store only allowed derived indicators in dossiers unless source agreements permit raw-data retention.
- Label each source as `demo`, `proxy`, `calibrated`, `real-data`, or `procurement-ready` through [[Claim Ledger]].

## Backups And Retention

Prototype retention classes:

| Class | Paths | Suggested Retention | Gap |
|---|---|---|---|
| Source snapshots | `data/`, `cache/graphs/` | per contract/source policy | no backup job |
| Run evidence | `data/runs/`, `reports/dossiers/`, `reports/workflows/` | project lifetime plus procurement archive | no restore drill |
| Registries | `docs/obsidian/03-registries/` | project lifetime | no signed export |
| Audit ledger | `.omx/ultragoal/ledger.jsonl`, workflow history | project lifetime | no append-only store |

## SLA And Security Posture

Current status is `demo`:

- No production SLA is claimed.
- No SSO/RBAC is implemented.
- No penetration test, vulnerability scan, SOC report, or hardening evidence is attached.
- Docker/compose is a prototype run path, not a certified deployment.

Minimum next evidence for stronger claims:

- authenticated roles
- backup and restore test
- dependency/security scan
- network and secret-management design
- uptime/support model
- signed data-processing and hosting review

## Training And Acceptance Checklist

| Acceptance Item | Evidence | Status |
|---|---|---|
| Generate one Abay dossier | `reports/dossiers/abay-signal-retiming/dossier.md` | prototype |
| Explain KPI formulas and limitations | `docs/analytics_contract.md` | prototype |
| Produce run passport | `data/runs/abay-signal-retiming-run-passport.json` | prototype |
| Move dossier through workflow | `reports/workflows/abay-signal-retiming-decision-workflow.json` | prototype |
| Export engineer tasks | `reports/workflows/abay-signal-retiming-decision-workflow-engineer-tasks.csv` | prototype |
| Attach post-audit comparison | `reports/workflows/abay-signal-retiming-decision-workflow-post-audit.json` | demo |
| Review tender checklist | `reports/procurement/tender_checklist.json` | demo |

## Three-Year TCO Framing

Use categories, not unsourced fixed prices:

| Cost Category | Year 1 | Years 2-3 | Current Evidence Gap |
|---|---|---|---|
| Deployment and hosting | on-prem/container setup | maintenance and infrastructure refresh | no municipal hosting quote |
| Data integrations | source onboarding and legal review | feed monitoring and adapter updates | no city source agreement |
| Calibration and validation | corridor calibration | periodic recalibration and audits | no observed outcomes attached |
| Training and support | initial operator/planner training | refresher training and support desk | no signed support model |
| Product maintenance | bug fixes and feature hardening | upgrades, security patches, acceptance support | no SLA |

## Tender Checklist Artifact

Generate:

```bash
PYTHONPATH=src python3 scripts/generate_procurement_packet.py --out reports/procurement
```

Review:

- `reports/procurement/tender_checklist.json`
- `reports/procurement/tender_checklist.csv`
