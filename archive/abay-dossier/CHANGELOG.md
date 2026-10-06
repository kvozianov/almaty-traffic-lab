# Changelog

## 2026-08-11

- Reframed the repository around one portfolio-ready Abay Scenario Dossier rather than a generic traffic dashboard.
- Added a deterministic paired signal-delay proxy with closed configuration, aggregate-demand controls, explicit occupancy/source-scale assumptions, JSON Schema validation, and semantic fingerprints.
- Added claim-safe KPI/recommendation logic: the active result remains `proxy` and requests more evidence instead of presenting a funding decision.
- Added one transactional bootstrap that validates a declared source slice, builds the complete evidence graph in staging, promotes an immutable run atomically, and verifies rollback/tamper/mixed-run cases.
- Bound the Next.js dossier, API, and map to verified immutable release artifacts; production generation remains disabled.
- Added portfolio README/method/validation documentation, responsive browser evidence, and Obsidian goal/claim/artifact handoffs.

## 2026-06-05

- Added a first-epic reproduction path with `simulation.config.json` and `scripts/reproduce_dossier.py`.
- Added reproduction metadata, artifact manifest, and hourly trajectory CSV export for the Abay dossier path.
- Documented the local reproduction command in `README.md` and `README_METHODS.md`.
