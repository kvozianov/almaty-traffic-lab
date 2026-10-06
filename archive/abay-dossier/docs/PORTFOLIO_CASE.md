# Portfolio Case: Evidence-Gated Mobility Decision Dossier

Kirill designed and implemented an evidence-centred scenario dossier for a proposed Abay Avenue signal-retiming case in Almaty. The goal was to make a municipal-style decision review inspectable: a controlled scenario configuration produces serialized KPIs, a run passport, source fingerprints, limitations and procurement/data-readiness evidence, all delivered through a validated web dossier.

The technical approach combines Python generation contracts, immutable release transactions, JSON Schema and SHA-256 verification, and a Next.js presentation layer that reads only verified evidence. The public interface is English-first, accessible, responsive, printable, and exposes five hash-verified download artifacts from the same immutable run.

What is verified: closed artifact contracts, controlled-pair consistency, repeatable semantic/KPI evidence, read-only production boundaries, safe downloads, and browser accessibility/responsive checks. What is not claimed: field calibration, live traffic prediction, procurement readiness, or automatic signal control. The current model result is explicitly `proxy`.

Stack: Python, JSON Schema, Next.js, React, TypeScript, MapLibre/deck.gl, Playwright, axe, ESLint, Docker Compose, and Git-based release verification.

Project links, citation identity, licence and release tag are intentionally omitted until the project owner approves the entries in `docs/releases/v0.1.0-owner-decisions.md`.
