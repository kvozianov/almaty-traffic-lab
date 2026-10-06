---
title: G014 - Almaty Traffic Lab
project: Almaty Mobility Decision Platform
type: ultragoal-function
goal_id: G014
goal_title: Almaty Traffic Lab
goal_status: in-progress
product_status: implemented-local
priority: P0
owner: Kirill
first_epic: false
claim_level: proxy
depends_on:
  - "[[G002 - Scenario Dossier MVP]]"
  - "[[G012 - Reproducibility And Deployment]]"
next_action: Deploy to Vercel, merge traffic-lab into main, make the repository public, add the live URL to README and the resume.
acceptance_gate: A reviewer opens the public link without setup, runs an example and an own scenario in under three minutes on desktop and phone; CI green; engine, data and visitor-flow tests pass.
tags:
  - almaty/goal
---

# G014 - Almaty Traffic Lab

## Why

The project is a portfolio piece for a university application. Reviewers must be able to choose a problem themselves and test it in the browser, without installing anything. The fixed Abay dossier answered one question; the lab lets visitors ask their own. Plan: `docs/PLAN_ALMATY_TRAFFIC_LAB.md`; design: `docs/TECH_DESIGN.md`.

## What Changed (2026-10-06, branch `traffic-lab`)

- Offline data pipeline `scripts/lab/`: OSM snapshot → road graph (3,505 nodes, 6,871 directed edges, 665 signals, 932 sections, English names) → 135-zone gravity demand → plausibility calibration (275,000 AM trips, ~27 km/h) → baselines + SHA-256 manifest in `public/model/`.
- In-browser engine `src/lab/engine/`: path-based user equilibrium (gradient projection) warm-started from baseline routes; conjugate Frank–Wolfe reference; interventions close / bus lane / add lane / green priority / 40 km/h / development; metrics; deterministic hashing.
- Web app: home, `/lab`, `/lab/report`, `/methods`; native MapLibre 6 rendering; shared Web Worker pre-warmed on the home page.
- Old dossier web layer, Python-backed API routes, deck.gl and Tailwind removed; release tooling moved to `archive/abay-dossier/`. Python package and its 109 tests unchanged in behaviour.

## Verification

- `npm run test:engine` — 16 tests (equilibrium vs Frank–Wolfe, flow conservation, closures, green-priority trade-off, development trips, determinism, speed).
- `python -m unittest tests/test_lab_data.py` — byte-identical data rebuild.
- `node tests/e2e/visitor-flow.mjs` against a production build — 12/12 steps on desktop and phone, axe: no serious/critical violations.
- `npm audit --omit=dev` — 0 vulnerabilities.

## Claim Boundary

Roads and signals: `real-data` (OSM snapshot). Capacities: `proxy` (engineering defaults). Demand and calibration: `proxy` (no OD survey, no observed travel times). The UI says so in “How much to trust this”. Do not describe results as forecasts.

## Unresolved Risks

- Demand concentrates on Al-Farabi / Rysqulov (V/C > 2); spatial demand proxy over-weights low-density private-house districts.
- No validation against measured travel times (planned P2: sample route times by period).
- Browser solve time depends on device; ~2 s per example on a laptop, slower on old phones.

## Next Action For The Next Agent

Deploy (Vercel, Node 22), confirm the public URL on desktop and phone, merge `traffic-lab` into `main`, make the repo public, add the live URL to README and the resume entry.
