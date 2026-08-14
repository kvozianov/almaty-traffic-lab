---
title: G012 - Reproducibility And Deployment
project: Almaty Mobility Decision Platform
type: ultragoal-function
goal_id: G012
goal_title: Reproducibility And Deployment
goal_status: completed
product_status: implemented
priority: P1
owner: Shared
first_epic: true
claim_level: demo
depends_on:
  - G002
  - G005
next_action: Validate the reproduction path on a clean checkout or Docker-capable host before making procurement-ready claims.
acceptance_gate: A clean checkout can reproduce the same scenario report artifacts from fixed seed and documented commands.
tags:
  - almaty/goal
  - ai-agent/workbench
  - almaty/first-epic
aliases:
  - G012 Reproducibility
---

# G012 - Reproducibility And Deployment

## Council Verdict

If the platform only works on the original machine, it is not procurement-ready. Separate two proofs: reproduce a dossier and run locally/on-prem.

## Implementation Move

Create the blessed path:

- `simulation.config.json`
- seed propagation
- per-run artifact folder
- `metadata.json`
- trajectory CSV/Parquet export
- `scripts/reproduce_dossier.py`
- Docker Compose validation
- `README_METHODS.md`

## Files To Touch First

- `simulation.config.json`
- `src/traffic_sim/config.py`
- `src/traffic_sim/run_metadata.py`
- `scripts/reproduce_dossier.py`
- `docker-compose.yml`
- `README_METHODS.md`

## Acceptance Gate

`PYTHONPATH=src python3 scripts/reproduce_dossier.py --config simulation.config.json --out reports/repro/abay`

The command regenerates dossier artifacts, metadata, and trajectory export from a fixed seed.

## Avoid

- Manual setup hidden in chat history.
- "Docker later" if procurement claims mention on-prem.
- Reproducibility without data/source versions.

## Evidence Links

- [[G002 - Scenario Dossier MVP]]
- [[G005 - Data Trust And Audit Layer]]
- [[Artifact Registry]]

## Agent Handoff

### 2026-06-05 - One-Command Reproduction Path Implemented

- Changed: added a root `simulation.config.json` with embedded Abay scenario, typed reproduction config loader, reproduction module, CLI script, README/runbook documentation, changelog, deterministic tests, and the generated Abay first-epic reproduction folder.
- Files touched: `simulation.config.json`, `src/traffic_sim/config.py`, `src/traffic_sim/reproducibility.py`, `src/traffic_sim/run_metadata.py`, `src/traffic_sim/dossier.py`, `scripts/generate_analytics.py`, `scripts/reproduce_dossier.py`, `tests/test_reproducibility.py`, `README.md`, `README_METHODS.md`, `CHANGELOG.md`, `reports/repro/abay/metadata.json`, `reports/repro/abay/artifact_manifest.json`, `reports/repro/abay/trajectory.csv`, `reports/repro/abay/portfolio/kpi_matrix.csv`, `reports/repro/abay/run-passport.json`, `reports/repro/abay/data_sources/`, `reports/repro/abay/dossier/`, `reports/repro/abay/workflows/`, `reports/repro/abay/procurement/`, `reports/repro/abay/research_metrics/`.
- Verification: `PYTHONPATH=src python3 -m compileall -q src/traffic_sim scripts`; `PYTHONPATH=src python3 -m unittest tests.test_reproducibility`; `PYTHONPATH=src python3 scripts/reproduce_dossier.py --config simulation.config.json --out reports/repro/abay`; `python3 -m json.tool reports/repro/abay/metadata.json`; `python3 -m json.tool reports/repro/abay/artifact_manifest.json`; trajectory assertion for 48 rows across baseline and measure; manifest assertion for 21 artifacts with SHA-256 hashes and road status `real-data`; run-passport assertion for `proxy` calibration and local provider paths; path traversal rejection tests.
- Claim labels changed: reproducible clean run moved from not implemented to `demo`; dossier/KPI/research/trajectory values remain `proxy`; road geometry remains `real-data` snapshot; no `procurement-ready` claim was added.
- Blocked verification: `docker compose config` remains blocked because Docker is not installed in this shell.
- Unresolved risks: run timestamps and git dirty count vary by machine; trajectory export is hourly analytics time series, not raw GPS/probe traces; Docker path is documented/prototype but not validated here; road geometry `real-data` evidence depends on the source snapshot being present and downgrades if unavailable.
- Next action: run final Ultragoal mandatory cleanup/review gate and record any blockers before marking the aggregate goal complete.

### 2026-06-05 - Final Cleanup And Review Gate Passed

- Changed: completed the scoped anti-slop cleanup for the reproduction path, narrowed broad exception handlers to explicit filesystem/JSON/subprocess boundaries, clarified the reproduced road-provider artifact kind, regenerated the Abay reproduction bundle, and completed the independent final review gate.
- Files touched: `scripts/generate_analytics.py`, `src/traffic_sim/reproducibility.py`, `src/traffic_sim/run_metadata.py`, `reports/repro/abay/metadata.json`, `reports/repro/abay/artifact_manifest.json`, `reports/repro/abay/trajectory.csv`, `reports/repro/abay/portfolio/kpi_matrix.csv`, `reports/repro/abay/run-passport.json`, `reports/repro/abay/data_sources/`, `reports/repro/abay/dossier/`, `reports/repro/abay/workflows/`, `reports/repro/abay/procurement/`, `reports/repro/abay/research_metrics/`.
- Verification: `PYTHONPATH=src python3 -m compileall -q src/traffic_sim scripts` passed; `PYTHONPATH=src python3 -m unittest tests.test_data_sources tests.test_procurement tests.test_research_metrics tests.test_reproducibility tests.test_workflow` passed; `PYTHONPATH=src python3 scripts/reproduce_dossier.py --config simulation.config.json --out reports/repro/abay` passed with 21 artifacts; `python3 -m json.tool` passed for `simulation.config.json`, reproduction metadata, artifact manifest, and run passport; semantic assertion proved 48 trajectory rows, local KPI matrix, deterministic analytics env marker, source fingerprints, local provider registry/status paths, and `proxy` calibration; stale-overclaim and fallback-smell scans returned no findings; `npm run lint`, `npm run build`, and `git diff --check` passed.
- Review gate: final code-review lane returned `APPROVE` with no blocking findings; final architecture/evidence lane returned `CLEAR` with no blocking findings; OMX checkpoint marked `G012-reproducibility-and-deployment` complete and reported 12/12 ultragoal stories complete.
- Claim labels changed: none in this gate; reproducible run remains `demo`, KPI/dossier/research/trajectory evidence remains `proxy`, and cached/imported road geometry remains `real-data` with non-live caveat.
- Blocked verification: `docker compose config` is still blocked because `docker` is not installed in this shell.
- Unresolved risks: clean-checkout/container reproduction still needs to be performed on a Docker-capable host; timestamps and dirty-state counts are machine-specific; trajectory CSV is hourly analytics output, not raw probe/GPS data; no procurement-ready claim is allowed until independent clean-run and acceptance evidence is attached.
- Next action: validate the same one-command reproduction path in a clean checkout or container and attach reviewer acceptance evidence before any claim upgrade.

### 2026-08-11 - Transactional Portfolio Bootstrap And Isolated Verification

- What changed: added `portfolio.sources.json`, an exact Python lock, a canonical bootstrap, immutable versioned run directories, an atomic `current.json` pointer, closed compatibility aliases, schema/hash/reference validation, rollback, contention handling and idempotent alias recovery. The release now materializes the one canonical reproduction configuration, pins the staging schema before generation, rejects parent/lock symlinks and binds every audit-bearing nested artifact to the same unique release run ID.
- Files touched: `portfolio.sources.json`; `requirements.lock`; `simulation.config.json`; `src/traffic_sim/config.py`; `src/traffic_sim/portfolio_release.py`; `scripts/bootstrap_portfolio.py`; `schemas/portfolio-route-manifest.schema.json`; `tests/test_portfolio_release.py`; `tests/test_portfolio_bootstrap.py`; `.gitignore`; `package.json`; `package-lock.json`; `README.md`; `README_METHODS.md`; `README_VALIDATION.md`.
- Verification: source slice `35/35` required with 13 pinned hashes; full suite `100/100`; current manifest 11 route artifacts and 43 aliases; rollback, lock contention, fsync seam, alias retry, traversal, parent/lock symlink, staging-schema replacement, nested tamper, stale-root, forged mixed-run, post-pointer exception/interrupt and explicit Git-proof-status cases passed. Once `current.json` names the installed run, later durability/notification errors are reported as `promoted_with_warning`; a BaseException in the atomic-replace window cannot delete the committed run. `docker compose config --quiet` passed. A fresh `/tmp` filesystem copy installs from `requirements.lock`, bootstraps before tests, and repeats Python/frontend checks; the committed clean-clone proof remains separate.
- Generated artifact: `reports/portfolio/current.json` pointing to a never-overwritten immutable run under `reports/portfolio/runs/`, plus `reports/portfolio/compatibility-aliases.json`.
- Unresolved risks: `trackedProof=pending_git_authorization` because the curated source slice has not been staged/committed; direct Windows reproduction is unsupported; best-effort POSIX fsync is not a universal power-loss guarantee; the map dependency audit still requires hardening before deployment.
- Claim labels changed: none. Reproducible application workflow remains `demo`; model/dossier outputs remain `proxy`.
- Next action: after explicit Git authorization, curate and commit the source slice, reproduce from a true clean clone/container, attach the commit ID and security scan, then request independent release acceptance.
