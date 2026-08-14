---
title: G011 - Research Metrics And Publication Visuals
project: Almaty Mobility Decision Platform
type: ultragoal-function
goal_id: G011
goal_title: Research Metrics And Publication Visuals
goal_status: completed
product_status: implemented
priority: P3
owner: Shared
first_epic: false
claim_level: proxy
depends_on:
  - G004
  - G005
  - G012
next_action: Proceed to [[G012 - Reproducibility And Deployment]] and include the research appendix in the one-command reproduction path.
acceptance_gate: Each selected metric has formula, deterministic endpoint/test, visualization/export field, and official-facing reason to exist.
tags:
  - almaty/goal
  - ai-agent/workbench
aliases:
  - G011 Research Metrics
---

# G011 - Research Metrics And Publication Visuals

## Council Verdict

Research metrics create credibility, but they can distract from the purchase decision. Keep publication mode separate from decision mode while sharing validated outputs.

## Implementation Move

Prioritize metrics that strengthen trust or ROI:

- reliability index
- emissions proxy
- sensitivity/confidence interval
- scenario KPI matrix
- one network heatmap or OD flow visual

Later:

- MFD
- PTI/TTR
- resilience
- Monte Carlo CIs
- time-space diagrams
- replay/scrubbing

## Files To Touch First

- `src/traffic_sim/research_metrics.py`
- `src/traffic_sim/analytics.py`
- `docs/analytics_contract.md`
- `src/components/TrafficMap.tsx`
- dossier appendix templates

## Acceptance Gate

Generated research metric artifacts can be cited from a dossier appendix and reproduced from the same run metadata.

## Avoid

- Beautiful charts that cannot be exported or reproduced.
- Research completeness before the first buyer dossier.
- Metrics with no official-facing purpose.

## Evidence Links

- [[G004 - Executive KPI Layer]]
- [[G005 - Data Trust And Audit Layer]]
- [[G012 - Reproducibility And Deployment]]

## Agent Handoff

### 2026-06-05 - Dossier Research Appendix Implemented

- Changed: implemented a dossier-adjacent research metrics pack for the Abay signal-retiming dossier with five selected metrics: reliability index, emissions proxy, person-hours sensitivity interval, scenario KPI matrix, and network-hour heatmap.
- Files touched: `src/traffic_sim/research_metrics.py`, `scripts/generate_research_metrics.py`, `tests/test_research_metrics.py`, `src/app/api/research-metrics/route.ts`, `src/traffic_sim/web_app.py`, `docs/research_metrics_contract.md`, `docs/analytics_contract.md`, `reports/research_metrics/abay-signal-retiming/research_metrics.json`, `reports/research_metrics/abay-signal-retiming/dossier_appendix.md`, `reports/research_metrics/abay-signal-retiming/research_visual.html`.
- Verification: `PYTHONPATH=src python3 -m compileall -q src/traffic_sim scripts`; `PYTHONPATH=src python3 -m unittest tests.test_research_metrics`; `PYTHONPATH=src python3 scripts/generate_research_metrics.py --dossier reports/dossiers/abay-signal-retiming/dossier.json --portfolio-matrix reports/portfolio/month1/kpi_matrix.csv --out reports/research_metrics/abay-signal-retiming`; `python3 -m json.tool reports/research_metrics/abay-signal-retiming/research_metrics.json`; targeted assertion harness for required metric IDs, formulas, official-facing reasons, 24 heatmap rows, `abay-signal-retiming` matrix winner, and `proxy` claim level; `npm run lint`; `npm run build`; live `curl http://localhost:3015/api/research-metrics`; in-app Browser route load for localhost API.
- Claim labels changed: research metrics appendix moved from not implemented to `proxy`; no `calibrated`, `real-data`, or `procurement-ready` research claim was added.
- Unresolved risks: sensitivity interval is a deterministic band, not Monte Carlo; heatmap is generated from existing analytics time series, not observed detector data; emissions remain G004 vehicle-hour proxies; no dashboard research-mode UI or OD/MFD/time-space visual was added; direct browser `file://` visual inspection was blocked by Browser URL policy, so the HTML/SVG visual was verified by file assertions.
- Next action: add `reports/research_metrics/abay-signal-retiming/` to the [[G012 - Reproducibility And Deployment]] reproduction script output checks.
