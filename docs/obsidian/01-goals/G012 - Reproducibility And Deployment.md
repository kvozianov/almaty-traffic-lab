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

### 2026-08-14 - M4 Runtime Dependency and Bootstrap-Wrapper Remediation

- What changed: removed the vulnerable `@deck.gl/geo-layers` production dependency by rendering sandbox vehicle paths with the maintained `PathLayer` from `@deck.gl/layers`; retained the sandbox route, its Carto disclosure, and the animated vehicle marker context. Fixed `npm run portfolio:bootstrap -- <args>` so it forwards arguments to the Python bootstrap rather than accidentally promoting a run. Added Node/npm/Python version pins and excludes all local `.env*` values from Git and Docker while retaining a value-free example.
- Files touched: `src/components/TrafficMap.tsx`; `package.json`; `package-lock.json`; `.node-version`; `.python-version`; `pyproject.toml`; `.gitignore`; `.dockerignore`; `.env.example`.
- Verification: sandbox and dossier browser-quality matrix passed after rebuild; `npm run portfolio:bootstrap -- --verify-current`; `npm run portfolio:bootstrap -- --verify-sources`; full Python 106-test suite; lint, typecheck and production build passed. `npm audit --omit=dev --audit-level=high --json` now reports zero high/critical runtime findings.
- Unresolved risks: full audit still has dev-tool findings introduced by the required legacy Lighthouse CI package; no exception has been self-approved. Docker-backed scanner/SBOM/license/clean-clone proof and owner release decisions remain later gates.
- Claim labels changed: none. The run remains `demo`; dossier/KPIs remain `proxy`; the sandbox remains clearly labelled demo/proxy.
- Next action: finish toolchain/lock, secret, SBOM and license controls without adding a release exception; execute the pinned Lighthouse and container gates only in their prescribed CI environment.

### 2026-08-14 - M5 Read-Only Candidate/Tag Verification Entrypoint

- What changed: added `npm run verify:release -- --stage candidate|tagged [--tag vX.Y.Z]`, backed by a repository-owned POSIX orchestrator. It validates its arguments, refuses a dirty index/worktree, rejects tracked ignored files, requires the requested tag at tagged stage, and runs only verification commands.
- Files touched: `scripts/verify-public-release.sh`; `package.json`.
- Verification: `--help` passed; invalid stage failed with exit `64`; candidate stage correctly failed on the existing dirty tree before any bootstrap/test command; lint, TypeScript and diff checks passed.
- Unresolved risks: a full candidate pass requires a clean committed tree and the remaining Docker/CI/security evidence. This local workspace is intentionally dirty, so candidate success is not claimed.
- Claim labels changed: none.
- Next action: add SHA-pinned CI workflows and run this same command from a clean candidate checkout; do not duplicate the verifier logic in workflows.

### 2026-08-14 - M5 Clean-Candidate Materialization Guard

- What changed: added a separate preparation command that clones the exact committed revision into a new absolute destination and invokes the canonical portfolio bootstrap there. It is deliberately separate from the read-only release verifier so preparation cannot be mistaken for verification and the candidate retains Git identity.
- Files touched: `scripts/prepare-release-candidate.sh`.
- Verification: POSIX shell syntax check passed; relative destination, existing destination and dirty source-tree negative paths all rejected with explicit diagnostics; `git diff --check` passed.
- Unresolved risks: a positive materialization run needs the pending source changes committed and a clean worktree. CI must install the locked JavaScript dependencies in the resulting disposable checkout before invoking the release verifier.
- Claim labels changed: none.
- Next action: use the materializer in the SHA-pinned candidate workflow after the current source slice is committed, then attach the clean-candidate command log and generated run hashes.

### 2026-08-14 - M5 Candidate Determinism, Browser Boundary, and Container Contract

- What changed: added a two-run isolated-bootstrap comparator that reports the paired semantic fingerprint, canonical KPI hash, source-manifest hash, and normalized release-bundle hash without changing the checkout. The release verifier now starts the production server for the three-browser/axe responsive test and checks the read-only API headers plus the production mutation `404`. The container is multi-stage, uses digest-pinned Node 20.20.0 and Python 3.14.2 bases, creates its immutable evidence pack during build, runs only production Node dependencies as `node`, and declares a health check. The Compose service has no mutable source/report bind mounts and drops Linux capabilities. A minimal-permission, SHA-pinned candidate workflow materializes a clean Git clone before running the same release command.
- Files touched: `scripts/verify_portfolio_determinism.py`; `scripts/verify-public-routes.sh`; `scripts/verify-public-release.sh`; `tests/portfolio_m3_quality.mjs`; `Dockerfile`; `docker-compose.yml`; `.dockerignore`; `.github/workflows/ci.yml`; `package.json`; `security-tools.lock.json`; `.semgrep.yml`; `.omx/evidence/portfolio-m5-ultraqa.md`.
- Verification: full Python suite `106/106`; lint; TypeScript; production build; English and download contracts; two-run comparator (`semanticFingerprint` `238e11b8…ec8c2`, canonical KPI hash `18d6702e…edd1b`, normalized bundle hash `c22b1518…92ebd`); production browser/axe/API boundary smoke; Compose config; runtime npm audit (`0` high/critical); and `git diff --check` all passed.
- Unresolved risks: local Docker daemon is unavailable, so image build/health/SBOM/CVE execution is not claimed. The workspace remains dirty, preventing a positive clean-candidate/tagged verifier run. Full npm audit is still blocked by required Lighthouse-CI dev-tool findings; no exception has been approved. The workflow has not yet run remotely.
- Claim labels changed: none. Workflow/container evidence remains `demo`; dossier and KPI results remain `proxy`.
- Next action: commit a reviewed source slice, run the candidate workflow and digest-pinned container/security scans, then obtain the owner decisions required for M6/tagged release.

### 2026-08-14 - M6 Documentation Drafts Without Owner Decisions

- What changed: added English architecture, six-minute demo and portfolio-case documents; aligned README quick start, Docker description and verification instructions to the pinned toolchains and candidate gate; corrected the validation document’s obsolete runtime Deck.gl vulnerability statement.
- Files touched: `README.md`; `README_VALIDATION.md`; `docs/ARCHITECTURE.md`; `docs/DEMO_SCRIPT.md`; `docs/PORTFOLIO_CASE.md`; `tests/docs_contract.mjs`; `scripts/verify-public-release.sh`; `package.json`.
- Verification: `npm run test:docs` verifies English public copy, required release drafts, source-backed README KPI values and key architecture/demo/claim wording; English source contract, lint, typecheck, production build and `git diff --check` remain green. All new result wording retains `demo`/`proxy` claim labels and avoids owner-only release metadata.
- Unresolved risks: M6 entry is still blocked by the owner-decision register, a clean M5 candidate, the final security/container evidence, and a tagged release. Citation, licence, security contact, repository URL and data-redistribution terms are deliberately not invented.
- Claim labels changed: none.
- Next action: owner approves the register, then add the final legal/citation/governance documents and bind documentation values/checksums to the tagged release manifest.

### 2026-08-14 - M4 Tracked-Ignored Hygiene Inventory

- What changed: recorded all 39 paths currently reported by `git ls-files -ci --exclude-standard`, separating Finder/bytecode caches, non-allowlisted legacy source data and ignored historical generated reports. The report recommends a non-destructive index cleanup while preserving local user data and explicitly does not request a history rewrite.
- Files touched: `docs/releases/v0.1.0-hygiene-inventory.md`.
- Verification: current hygiene command reported 39 paths and the report classifies every path; source allowlist and current runtime audit remain unchanged.
- Unresolved risks: REL-09 cannot pass until the owner authorizes index cleanup. No tracked ignored file was removed or modified here because these existing artifacts may be user-owned.
- Claim labels changed: none.
- Next action: obtain explicit cleanup authorization, remove approved entries from the release index without deleting needed local copies, then prove the empty hygiene result in a clean candidate.

### 2026-08-14 - M5 Actual Hardened Container Smoke

- What changed: removed the Dockerfile frontend syntax directive because it caused an implicit unpinned external frontend fetch before the repository's digest-pinned stages. The image now builds entirely through the declared pinned Node/Python bases and performs the immutable portfolio bootstrap during the build.
- Files touched: `Dockerfile`; `.omx/evidence/portfolio-m3-ultraqa.md`; `.omx/evidence/portfolio-m5-ultraqa.md`; `docs/obsidian/03-registries/Artifact Registry.md`.
- Verification: `docker compose build --progress plain` built `project1-citytraffic-app:latest` with manifest digest `sha256:3dcbdf2823599f70991ac19e2f7fc5d75940fc3a5084ce09cb0f1acacd9a2a1d`; its immutable build run was `abay-container-0`. `docker compose up --detach` reached a healthy non-root (`1000:1000`), read-only container. `GET /api/dossier` returned `200`, `Cache-Control: no-store`, the expected run/source headers, and the public mutation route returned `404`.
- Unresolved risks: the clean candidate is still blocked by the dirty Git workspace and the 39 tracked-and-ignored inventory entries. The digest-pinned MCR Lighthouse and Docker Hub Syft pulls both stalled at Docker credential retrieval, so no performance/SBOM/CVE results are claimed. Full npm audit still has nine high development-only findings through the required legacy Lighthouse-CI package.
- Claim labels changed: none. Container/runtime evidence remains `demo`; dossier/KPI results remain `proxy`.
- Next action: repair or authorize the Docker credential path, run the locked Lighthouse/Syft/Grype gates, then obtain explicit index-cleanup and release-tag authorization for a clean candidate.

### 2026-08-15 - M4/M5 Pinned Runtime Security Evidence

- What changed: executed the declared digest-pinned Syft, Grype and Semgrep tools through an isolated empty Docker configuration. This bypasses a local credential-helper stall without reading or changing saved credentials. It produced an SBOM and security reports for the exact locally built runtime image.
- Files touched: `reports/security/v0.1.0-runtime-sbom.cdx.json`; `reports/security/v0.1.0-runtime-grype.json`; `reports/security/v0.1.0-semgrep.json`; `.omx/evidence/portfolio-m3-ultraqa.md`; `.omx/evidence/portfolio-m5-ultraqa.md`; `docs/obsidian/03-registries/Artifact Registry.md`.
- Verification: Syft `v1.50.0` produced a CycloneDX 1.7 SBOM (4,072 components; SHA-256 `469dd1ae2efd5e2ad5371f6fa3843fa9fc779bd55bca576752437ad1c0e45950`) for `project1-citytraffic-app@sha256:3dcbdf2823599f70991ac19e2f7fc5d75940fc3a5084ce09cb0f1acacd9a2a1d`. Grype `v0.116.1` scanned it (SHA-256 `61babdf66f1d4b764a9ba9963444355fb4a1c4cde3bb6dcd01bb1717cab13e6c`) and found 10 critical/58 high matches. Semgrep `v1.153.0` scanned 49 tracked source files with the repository’s two rules and found zero results.
- Unresolved risks: this is evidence of failure, not a security pass. The final runtime image remains non-releasable under the zero-high/critical policy due to its pinned Node 20/Debian base. The required MCR Lighthouse image gets past credentials but its layer transfer stalls; no performance score is claimed. Candidate hygiene, clean Git identity and owner decisions remain blocked as previously recorded.
- Claim labels changed: none. Security evidence remains `demo`; dossier/KPI results remain `proxy`.
- Next action: select and validate a supported base-image remediation that passes Grype without an exception, complete the locked MCR Lighthouse run, then complete the owner-authorized clean candidate/tag path.

### 2026-08-15 - Reproducible Runtime Security Gate

- What changed: added `npm run security:scan-runtime`, backed by `scripts/scan-runtime-image.sh`, and added the same gate to the clean-candidate CI workflow after canonical candidate verification. The command pulls only the digest-locked scanners via an isolated empty Docker configuration, scans a saved archive of the named runtime image, writes SBOM/CVE/static-analysis/summary JSON and fails closed on any high/critical Grype finding or Semgrep result.
- Files touched: `scripts/scan-runtime-image.sh`; `package.json`; `.github/workflows/ci.yml`; `.omx/evidence/portfolio-m5-ultraqa.md`; `docs/obsidian/03-registries/Artifact Registry.md`.
- Verification: shell syntax check passed. `npm run security:scan-runtime` executed end-to-end against the exact local image and exited `1` with its generated summary: 4,072 SBOM components, 10 critical/58 high Grype matches, zero Semgrep findings and `passed=false`. This is the intended fail-closed result, not a security pass.
- Unresolved risks: this makes the gate enforceable but does not remediate the frozen runtime-base vulnerabilities. A Chainguard Node 26.7.0 comparison at digest `sha256:f6c05914…f4172` reduced the scan to two high OpenSSL findings, both with no listed fix, but still failed the zero-high policy. The candidate workflow will correctly fail until a supported scanned base passes or an owner-approved policy exception exists.
- Claim labels changed: none.
- Next action: owner selects a runtime base remediation or approves a bounded security exception with evidence; then rebuild and require the corresponding documented security threshold before enabling a release pass.

### 2026-08-14 - Public Portfolio Release Gates Specified

- What changed: specified an executable public-release path with separate read-only `candidate` and `tagged` verification stages, complete Git/run provenance, one canonical verification command, SHA-pinned CI, hash-locked toolchains, clean-clone determinism, hardened non-root container, security/SBOM/license evidence and versioned release governance.
- Files touched: `.omx/plans/portfolio-idealization-technical-specification.md`; `.omx/plans/portfolio-idealization-traceability.md`; this goal note; `docs/obsidian/03-registries/Artifact Registry.md`.
- Verification: current immutable route verification passed for 11 artifacts/43 aliases; source verification passed 35/35 and 13 hashes with the known `trackedProof=pending_git_authorization`; structural traceability is complete; independent reviewer returned `APPROVE` after release-order and security-stage dependencies were corrected.
- Generated artifact: release requirements REL-01..10 and SEC-01..06 with explicit milestones, tools, evidence paths and final Definition of Done.
- Unresolved risks: requirements are specified but not implemented. The npm runtime graph still has eight high findings, CI/tag/license/citation package does not exist, Python/build locks need stronger supply-chain treatment, and Docker is not self-contained.
- Claim labels changed: none. Release hardening cannot upgrade a model claim.
- Next action: implement the read-only bootstrap wrapper regression first, then pin toolchains/security scanners and close the clean Git/source proof before building the candidate/tagged release pipeline.

### 2026-08-14 - M0 Baseline Freeze And Traceability Gate

- What changed: added a machine-readable baseline snapshot, owner-decision register, scanner-lock seed, empty security-exception policy/schema, and the repository-owned traceability checker with malformed-input regression coverage.
- Files touched: `docs/releases/v0.1.0-baseline.json`; `docs/releases/v0.1.0-owner-decisions.md`; `security-tools.lock.json`; `security-policy.yaml`; `schemas/security-exception.schema.json`; `scripts/check_portfolio_spec_traceability.py`; `tests/test_portfolio_spec_traceability.py`; `.omx/evidence/portfolio-m0-ultraqa.md`.
- Verification: current release verified with 11 route artifacts/43 aliases; source slice verified 35/35 with 13 hashes; 100 Python tests; lint/typecheck/build; traceability checker passed 92/92 IDs and its three tests passed twice; repeated read-only verification preserved the current-manifest SHA-256.
- Generated artifacts: baseline snapshot, owner-decision register, security-control seeds, traceability checker, and UltraQA report.
- Unresolved risks: `trackedProof=pending_git_authorization` correctly remains because the pre-existing worktree is dirty; runtime npm audit reports 8 high findings in the Deck.gl loader chain; Semgrep needs a final exact archive digest before CI enablement; owner-only release decisions remain pending.
- Claim labels changed: none. The dossier/KPIs remain `proxy`; workflow/package evidence remains `demo`; road geometry remains non-live `real-data`.
- Next action: implement M1 English dossier-first shell without changing evidence authority, followed by M4 dependency remediation before any public release claim.
