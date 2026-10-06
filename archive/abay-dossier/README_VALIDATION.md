# Validation Status And Protocol

## Current Status

The Abay portfolio case is **not empirically calibrated**. Its present claim level is `proxy`: it demonstrates a controlled, deterministic sensitivity experiment and a reproducible evidence workflow. There is no completed observed-versus-simulated holdout table for the active paired model.

The word “validated” in this repository should currently mean only a named software or evidence check, never field accuracy without an attached observed dataset and error table.

## What Is Checked Today

| Evidence area | Current check | Claim meaning |
|---|---|---|
| Paired control | Same seed, base series, complete aggregate-demand object, modeled count, and context fingerprint; only signal delay is controlled to differ | `proxy` experiment comparability |
| Formula behavior | Equal-delay identity, direction, bounds, rounding, unclamped monotonicity, and trip-time reversibility | implementation correctness, not empirical accuracy |
| Demand | Exact aggregate-count rational identity for 500 modeled vehicles, with source primitive count 1,950 preserved separately | aggregate KPI scale only; no demand-response or OD equivalence |
| Determinism | Stable experiment semantic fingerprint and canonically identical KPI block for repeated declared inputs | reproducible computation |
| Contracts | Draft 2020-12 schema checks, closed objects, logical-path validation, and SHA-256 verification | artifact integrity |
| Recommendation | Mixed, missing, clamped, placeholder-sensitive, proxy, or provenance-only `real-data` evidence cannot produce a funding decision | claim-safe decision logic |
| Application | Python tests, lint, typecheck, production build, immutable API/page smoke, desktop and 390 px review; UI calibration is complete only with a `calibrated` claim and observed-vs-simulated rows | software quality evidence |
| Road geometry | Imported/cached source with provenance and attribution | `real-data` provenance for geometry only |

The exact latest pass/fail evidence belongs in the promoted manifest and the Obsidian Artifact Registry. A passing application test does not upgrade the experiment above `proxy`.

## What Is Not Established

The current repository does not establish:

- observed traffic-count, travel-time, or speed agreement for Abay;
- calibration or out-of-sample validation of a corridor/network model;
- field-measured signal plans, phase constraints, queues, or spillback;
- route-level or OD-demand equivalence;
- a measured relationship between the 1,950-vehicle source primitive snapshot and the separate 500-vehicle KPI scale;
- observed average vehicle occupancy (the active person-hour proxy uses `1.0`);
- measured bus punctuality, emissions, safety, or economic benefit;
- sourced municipal CAPEX/OPEX, ROI, or payback;
- live-feed freshness, service levels, security hardening, or legal approval;
- causal impact of the proposed measure;
- readiness for automatic signal control or a binding procurement decision.

The runtime production dependency audit currently reports zero high/critical findings after removing the vulnerable `@deck.gl/geo-layers` chain. A complete release security claim still awaits the full dev-tool, Python, container, SBOM, license and secret-scan gates; it is not inferred from this runtime-only result.

The 36 s baseline and 32 s measure are declared proxy sensitivity values. They are not measurements of current and proposed controller timing.

## Provenance Is Not Calibration

The claim labels answer different questions:

| Label | Question answered |
|---|---|
| `demo` | Does the interface or workflow demonstrate a review process? |
| `proxy` | Is the simplified formula transparent and reproducible? |
| `real-data` | Did an input come from a real source with provenance, freshness, and usage constraints? |
| `calibrated` | Was model output compared with suitable local observations and visible error? |
| `procurement-ready` | Are acceptance evidence, limits, reproducibility, legal/security review, and buyer-safe language complete? |

One label does not imply another. In particular, imported road geometry can be `real-data` while `contextNetworkFingerprint.usedByModel` is false and the signal-delay model remains an uncalibrated `proxy`.

## Required Empirical Validation Protocol

The next evidence upgrade should be a preregistered corridor study, separate from the current proxy demonstration.

### 1. Define The Decision And Acceptance Thresholds

Before inspecting validation outcomes, record:

- target corridor extent and time windows;
- intended decisions and required accuracy for each KPI;
- sample-size and missing-data rules;
- error metrics and pass/fail thresholds;
- treatment of incidents, roadworks, weather, holidays, and sensor outages;
- data rights, retention, and permitted public disclosure.

Thresholds must be chosen for the decision context, not retrofitted to make a model pass.

### 2. Collect And Freeze Observed Inputs

Minimum candidate evidence:

- timestamped link or screenline counts with location/direction metadata;
- probe or surveyed travel times and speeds;
- current signal phase/timing plans and controller constraints;
- turning counts and queue observations at affected intersections;
- public-transport arrival/departure observations for reliability checks;
- incident, weather, roadwork, and calendar annotations;
- sourced cost and emissions assumptions if economic/environmental KPIs are assessed.

Each dataset needs source, acquisition time, spatial/temporal coverage, units, license/legal mode, cleaning steps, missingness, and a content hash.

### 3. Separate Calibration And Holdout Sets

Freeze a calibration set for parameter fitting and a holdout set that is not used during fitting. Keep representative peak/off-peak periods and atypical conditions visible rather than removing them without a stated rule.

### 4. Compare With Visible Error

Report sample counts and distributions, not only averages. Candidate metrics include:

- MAE and RMSE for travel time and speed;
- MAPE only where denominators and zero handling are explicitly safe;
- GEH-style statistics for traffic counts;
- queue-length and bus-reliability errors by location and time window;
- bias and residual plots;
- uncertainty or sensitivity intervals for scenario deltas.

Publish both calibration-set and holdout-set results, including failed corridors/time periods. A single city-wide summary is insufficient.

### 5. Review Scenario Causality Separately

Matching a baseline does not prove the effect of a signal intervention. Review controller feasibility, compare against a field pilot or defensible quasi-experimental design, record concurrent changes, and run forecast-versus-fact post-audit before presenting causal benefits.

### 6. Attach Evidence And Upgrade Deliberately

An upgrade to `calibrated` requires, at minimum:

- immutable observed-input manifests;
- documented calibration/holdout split;
- visible metric definitions and error tables;
- limitations and failed tests;
- model/config version and reproduction command;
- independent technical review recorded in the Claim Ledger.

An upgrade to `procurement-ready` additionally requires sourced costs, buyer acceptance criteria, security/legal/data-residency review, deployment proof, operational ownership, and a signed review process. No software test alone can provide that upgrade.

## Reviewer Checklist

- [ ] The promoted dossier and paired result both show `proxy`.
- [ ] Baseline and measure contain canonically equal aggregate-demand controls.
- [ ] Source primitive count 1,950 and modeled KPI scale 500 are visible as separate assumptions; occupancy 1.0 is explicit.
- [ ] The only controlled input difference is signal delay.
- [ ] `contextNetworkFingerprint.usedByModel` is false.
- [ ] KPI values in the README match the promoted artifacts exactly.
- [ ] Costs and economics expose placeholder state.
- [ ] Recommendation factors and evidence limitations are serialized.
- [ ] Repeated bootstrap preserves semantic fingerprints.
- [ ] No empirical-accuracy claim appears without observed rows and errors.
- [ ] Claim Ledger levels are unchanged unless new evidence was reviewed.

For the computation contract, see [README_METHODS.md](README_METHODS.md). For current claim ownership, see the [Claim Ledger](docs/obsidian/03-registries/Claim%20Ledger.md).
