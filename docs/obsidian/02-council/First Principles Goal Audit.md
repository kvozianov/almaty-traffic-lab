---
tags:
  - almaty-traffic
  - almaty/council
  - ai-agent
  - ultragoal
  - procurement
created: 2026-06-05
---

# First Principles Goal Audit

## G001 Baseline MVP Inventory

- Core job-to-be-done: Preserve the real pitchable surface and stop future work from breaking or overstating the current demo.
- Best minimal implementation: Create a capability inventory that maps each UI surface, API route, dataset, export, and screenshot to `implemented`, `partial`, `stub`, or `derived`, with smoke commands and evidence links.
- Decisive tradeoff: Inventory and guard what already works before adding more polish.
- One acceptance signal: A new agent can run the app, verify core endpoints, capture the baseline screenshots, and cite what is real vs assumed.

## G002 Scenario Dossier MVP

- Core job-to-be-done: Give akimat a defensible decision packet for one corridor measure, not a simulation demo.
- Best minimal implementation: Add a dossier service that takes a typed scenario, runs baseline vs variant analytics, computes KPI deltas, attaches assumptions/sources/risks/CAPEX/OPEX placeholders, and exports Markdown/PDF/XLSX through an API and UI action.
- Decisive tradeoff: One credible Abay-style corridor dossier beats a generic report builder.
- One acceptance signal: A baseline-vs-measure dossier exports for one real Almaty corridor with KPI deltas, assumptions, source metadata, and review-ready PDF/Excel artifacts.

## G003 ScenarioPortfolio And Batch Runner

- Core job-to-be-done: Let municipal users compare interventions as a portfolio of choices.
- Best minimal implementation: Define a `ScenarioPortfolio` schema/model and a batch runner that loads 3-5 scenario presets, runs them against one baseline, and emits a comparable KPI matrix as JSON/CSV.
- Decisive tradeoff: Structured config and batch output now; rich portfolio UI later.
- One acceptance signal: One command runs at least three municipal scenarios and produces a ranked, comparable result table.

## G004 Executive KPI Layer

- Core job-to-be-done: Translate simulation behavior into executive language: time, money, service quality, emissions, and risk.
- Best minimal implementation: Extend the analytics contract with person-hours lost/saved, corridor speed delta, queue proxy, bus reliability proxy, CO2/NOx proxy, CAPEX/OPEX, ROI/payback, and assumption fields.
- Decisive tradeoff: Use transparent first-order proxies before complex economics.
- One acceptance signal: The API and dossier both include an executive KPI block that explains effect, cost, and confidence for the scenario.

## G005 Data Trust And Audit Layer

- Core job-to-be-done: Make every recommendation inspectable enough to survive procurement and technical review.
- Best minimal implementation: Attach a run metadata object to every scenario/report: data sources, calibration date, observed-vs-simulated corridor table, model error, seed, git hash, data version, parameters, and limitations.
- Decisive tradeoff: Honest lineage and limitations over false precision.
- One acceptance signal: Every exported dossier includes a trust appendix with reproducible run ID, source list, calibration evidence, and scenario parameters.

## G006 Municipal Scenario Library

- Core job-to-be-done: Let akimat ask questions in municipal terms instead of simulation primitives.
- Best minimal implementation: Add scenario presets for road repair, accident, signal retiming, bus priority, bus lane, BRT corridor, school zone, snow/weather, paid parking, event surge, and development impact, each mapped to deterministic graph/demand/cost modifiers.
- Decisive tradeoff: Shallow but reliable presets before deeply customizable policy modeling.
- One acceptance signal: A user can select or call each preset and receive a valid scenario object usable by the dossier runner.

## G007 Operational Mode And Recommendations

- Core job-to-be-done: Support same-day operator decisions when an incident or disruption appears.
- Best minimal implementation: Add an incident input/API, 30/60/120 minute forecast using the scenario runner, and a recommendation template for detours, signal changes, affected corridors, and operator actions.
- Decisive tradeoff: Practical advisory playbooks before real-time optimization.
- One acceptance signal: Creating an incident returns a forecast plus three ranked actions with expected KPI impact and affected roads.

## G008 Closed Decision Workflow

- Core job-to-be-done: Turn scenario analysis into accountable city action and post-implementation learning.
- Best minimal implementation: Add a persisted status model: `draft -> reviewed -> approved -> assigned -> deployed -> monitored -> audited`, with history, owner, timestamps, task export, and forecast-vs-fact comparison.
- Decisive tradeoff: A simple auditable state machine before enterprise workflow tooling.
- One acceptance signal: One scenario can move from draft to post-audit while preserving decision history and comparing forecast to observed outcome.

## G009 Enterprise And Procurement Readiness

- Core job-to-be-done: Answer whether a municipality can buy, host, govern, audit, and accept the platform.
- Best minimal implementation: Create `docs/procurement.md` covering roles, audit log, scenario versioning, on-prem/Docker deployment, Kazakhstan data residency, SLA/security posture, training, acceptance checklist, and 3-year TCO framing.
- Decisive tradeoff: Tender-grade evidence and operating model before full enterprise security implementation.
- One acceptance signal: A procurement checklist maps each buyer requirement to implemented/prototype/planned evidence and a local/on-prem run path.

## G010 Real Data Integrations

- Core job-to-be-done: Replace demo assumptions with refreshable, attributable city data.
- Best minimal implementation: Define provider interfaces and status metadata, refresh OSM roads, add CSV import, prepare GTFS bus import, and document legal/technical adapters for Yandex, 2GIS, Sergek, Onay, and camera feeds.
- Decisive tradeoff: One clean provider contract before many fragile integrations.
- One acceptance signal: A user can refresh or import one real source and see source freshness, provenance, and provider status in API/UI output.

## G011 Research Metrics And Publication Visuals

- Core job-to-be-done: Add technical credibility only where it strengthens trust, ROI, or defensibility.
- Best minimal implementation: Prioritize reliability index, emissions proxy, sensitivity/confidence intervals, scenario KPI matrix, and one network heatmap or OD flow visual before broader research metrics.
- Decisive tradeoff: Buyer-critical evidence before academic completeness.
- One acceptance signal: Each selected metric has a deterministic endpoint/test and at least one visualization or dossier appendix use.

## G012 Reproducibility And Deployment

- Core job-to-be-done: Let a reviewer reproduce the exact decision artifact from a clean environment.
- Best minimal implementation: Add `simulation.config.json`, fixed seed propagation, per-run `metadata.json`, artifact folders, trajectory export, Docker Compose, and `README_METHODS` with one-command dossier reproduction.
- Decisive tradeoff: One blessed reproducible path before supporting every deployment variation.
- One acceptance signal: A fresh checkout can run one command and regenerate the same scenario JSON, PDF/XLSX dossier, and metadata.

## Cross-Cutting Principles

1. Build the decision artifact first: the platform sells when it produces a defensible municipal dossier, not when the simulation looks impressive.
2. Make evidence travel with every output: every KPI needs source, assumption, uncertainty, run ID, and owner.
3. Define schemas before screens: scenario, portfolio, KPI, dossier, run metadata, and workflow contracts should lead implementation.
4. Optimize for repeatability on 1-2 corridors before city-wide generality: narrow proof beats broad but thin coverage.
5. Separate planning and operations: Scenario Dossier and Operational Mode can share the engine, but they need different workflows, UI language, and acceptance tests.
