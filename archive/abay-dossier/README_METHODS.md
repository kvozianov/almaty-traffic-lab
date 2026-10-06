# Methods And Reproducibility

This document defines the method used by the portfolio Abay signal-retiming case. The method is intentionally bounded: it creates a controlled aggregate-count sensitivity experiment and a reviewable evidence dossier. It does not claim to reproduce field traffic operations.

## Evidence Chain

```text
declared source manifest
  -> controlled paired experiment
  -> run metadata + executive KPIs
  -> scenario dossier
  -> workflow / research / procurement evidence
  -> immutable portfolio run
  -> promoted route manifest
```

`portfolio.sources.json` is the allowlist for domain, configuration, fixture, schema, and upstream-artifact inputs. Generators receive one run context and in-run upstream artifact map. A generator may not silently reopen mutable root evidence that is absent from the source manifest.

## Paired-Experiment Contract

The result is serialized as a versioned `PairedExperimentResult` using the bounded model ID `abay-signal-delay-proxy-v1`. Baseline and measure share:

- scenario and corridor identity;
- seed and base analytics series;
- the complete closed `demandControl` object;
- modeled vehicle count;
- a context-only road-network fingerprint;
- formula version, bounds, units, and rounding rules.

The only controlled input difference is the signal-delay sensitivity value: `36 s` for baseline and `32 s` for measure. Derived analytics and KPIs are expected to differ. The signal values are proxy inputs, not field-observed controller plans.

### Demand Control

Proxy-v1 consumes aggregate demand count, not OD trips. Its closed control has this meaning:

```text
mode: aggregate-count-v1
modeledVehicleCount: 500
sourcePrimitiveVehicleCount: 1950
seed: injected from the closed reproduction config and shared by both variants
pattern: shared by both variants
source: compact fixture path + SHA-256 provenance + `sampleTripCount`
expansion: exact rational numerator / denominator
```

The compact fixture is `data/fixtures/abay/aggregate-demand.proxy-v1.json`. It retains an aggregate count and the provenance hash of the original source snapshot; raw trip records are outside the portfolio source slice. It deliberately contains no seed: `simulation.config.json` is the single seed source, and the release adapter injects that value into the demand control, pair, dossier, and run passport. `sourcePrimitiveVehicleCount=1950` records the count attached to the source time/speed/congestion primitives. It is not treated as modeled demand. The absolute KPI scale is independently fixed at `modeledVehicleCount=500`, and proxy-v1 does not model demand-response scaling between 1,950 and 500. The run must satisfy the exact integer identity:

```text
modeledVehicleCount × denominator = sampleTripCount × numerator
```

The bootstrap rejects a non-positive denominator or a result that would require rounding. Canonical deep equality of the full `demandControl` object is required between variants. This is an aggregate-count control, not evidence that individual trips, routes, or OD pairs are identical.

## Signal-Delay Proxy

All calculations use finite, unrounded values until the declared serialization boundary.

Let:

- `d` be the signal-delay sensitivity input in seconds;
- `a` be affected signals per trip (`4` in the active fixture, allowed `1..20`);
- `f` be realization factor (`0.55` in the active fixture, allowed `0..1`);
- `T_base` be source baseline average trip time;
- `C_base` be source baseline congestion index.

The equations are:

```text
S(d) = a × d × f
R = T_base - S(36)
T(d) = R + S(d)
q(d) = T(d) / T(36)
```

The run is rejected when `R <= 0`, a denominator/result is non-finite, or `q(d) <= 0`. Delay must be within `0..120 s`.

Serialized summary values:

```text
average_trip_time_seconds(d) = round(T(d), 2)
congestion_index(d) = round(clamp(C_base × q(d), 0, 100), 2)
```

For each source hour `i`:

```text
hour(d) = hour_base
congestion_index_i(d) = round(clamp(C_i × q(d), 0, 100), 2)
avg_speed_kph_i(d) = round(clamp(speed_i / q(d), 5, 80), 1)
```

`ml_forecast` and `node_throughput` are copied unchanged and listed under `unchangedFields`; proxy-v1 does not model the measure’s effect on either. The road-network fingerprint is retained for provenance with `usedByModel: false` and must not be interpreted as a causal network input.

Every variant is generated from the same unrounded baseline primitives, never from another transformed variant. Equal delays therefore produce semantic identity; in an unclamped range, reducing delay decreases trip time and congestion and increases speed. A symmetric delay perturbation is symmetric in `T(d)`, while ratio-derived speed and congestion are checked for direction and monotonicity rather than equal-sized deltas.

## KPI Layer

The dossier rebuilds KPIs from the selected pair after removing any embedded/stale KPI blocks from source analytics.

The explicit downstream proxy equations include:

```text
queue_load = congestion_index / 100
bus_reliability = clamp(95 - congestion_index × 0.45 + average_speed_kph × 0.08, 35, 98)
emissions_kg = T(d) × modeled_vehicle_count / 3600 × kg_per_vehicle_hour
person_hours = T(d) × modeled_vehicle_count × average_vehicle_occupancy / 3600
```

`average_vehicle_occupancy=1.0` is an explicit proxy assumption. Without it, the dimensional result would be vehicle-hours rather than person-hours. The active numeric outputs remain unchanged at occupancy 1.0, but neither occupancy nor time valuation is presented as observed local evidence.

Economic values use the configured CAPEX/OPEX inputs and remain placeholder-sensitive. The dossier separately evaluates:

1. mobility evidence: person-hours, speed, queue, bus-reliability, CO2, and NOx proxy directions;
2. economics evidence: completeness, placeholder state, ROI, and payback;
3. claim level: `demo`, `proxy`, `calibrated`, `real-data`, or `procurement-ready`.

Missing, clamp-affected, mixed, neutral-only, or placeholder-sensitive evidence requests more evidence. At `proxy` level the recommendation cannot become an unconditional funding decision, even when all modeled mobility directions are favorable. `real-data` refers only to input provenance and never bypasses the independent model-calibration gate.

## Semantic Reproducibility

Canonical JSON uses sorted keys and a declared volatile-field exclusion list:

```text
/semanticFingerprint
/generatedAt
/provenance/generatedAt
/provenance/sourceControl
/outputs
```

Other fields participate in the semantic SHA-256 fingerprint. Closed JSON schemas reject undeclared fields instead of silently excluding new timestamps or mutable metadata.

A repeated run may have a different release ID or generation time, but the controlled experiment's semantic fingerprint and the canonical KPI block must remain identical for the same declared inputs.

## Transactional Portfolio Release

`npm run portfolio:bootstrap` invokes the canonical release transaction:

1. acquire the POSIX release lock;
2. generate the complete dependency graph under one staging root;
3. validate JSON schemas, run IDs, logical references, and SHA-256 hashes;
4. reject absolute paths, traversal, symlink escape, mixed runs, and physical staging paths;
5. flush files/directories on a best-effort POSIX basis;
6. rename the validated staging run to a never-overwritten immutable run directory;
7. atomically replace `reports/portfolio/current.json`;
8. refresh non-authoritative legacy aliases after promotion.

A pre-promotion failure leaves the previous current pointer readable. Once the atomic pointer names the new run, later durability or notification exceptions are reported as `promoted_with_warning`; even an interrupt in the replace-return window cannot trigger destructive rollback of that visible run. A post-promotion alias failure also does not invalidate the promoted run and can be retried. This is an atomic-reader and process-failure guarantee on the documented local POSIX path, not a guarantee against every filesystem, hardware, or power-loss failure.

The web dossier, procurement-pack GET, and read-only APIs consume only the promoted or explicitly pinned immutable run. The server closed-validates the in-run source manifest and every required materialized source; the map binds its road request to the SSR run ID and expected source hash and rejects a mixed response. Both portfolio-generation POST routes are disabled by default and in production; the UI does not invoke them. In the opt-in development boundary, procurement generation delegates to the same canonical transaction, the child process receives an explicit non-secret environment allowlist, and the returned bootstrap run ID and pack hash must match the pinned immutable run.

## Reproduction Commands

Quick local installation can use `python -m pip install -e .`. The isolated verification path uses the exact generated lock and then installs the project itself without re-resolving dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.lock
python -m pip install --no-deps -e .
npm ci
TRAFFIC_SIM_PYTHON=.venv/bin/python npm run portfolio:bootstrap
```

The checked lock was generated from `pyproject.toml` on Python 3.14.5. `pyproject.toml` remains the compatibility contract (`Python >=3.11`); `requirements.lock` is the exact isolated-review environment.

Verification:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v
npm run lint
npx tsc --noEmit --pretty false --incremental false
npm run build
docker compose config
```

Supported direct reproduction is macOS or Linux. Docker is the supported container path. Direct Windows bootstrap is outside this release because locking, rename, and directory durability semantics are POSIX-specific.

## Method Limits

- No observed signal plan is used to set `36 s` or `32 s`.
- No individual route, OD pair, turning movement, or controller phase is modeled by proxy-v1.
- No queue propagation, spillback, lane-changing, or network assignment is inferred from the aggregate formula.
- The source analytics primitives carry a 1,950-vehicle provenance count, while absolute KPI scale uses an independent 500-vehicle aggregate control; no demand-response scaling is modeled.
- Average vehicle occupancy is fixed to the explicit proxy assumption `1.0`; person-hours and economic time value are not field estimates.
- Cached/imported geometry is context and provenance, not an input to the proxy formula.
- Emissions factors, time valuation, CAPEX, and OPEX need sourced local evidence before stronger use.
- Formula correctness and deterministic software behavior do not establish empirical accuracy.
- A future calibrated engine may implement the same paired-result contract, but its evidence must be evaluated separately.

For empirical status and the required calibration study, see [README_VALIDATION.md](README_VALIDATION.md).
