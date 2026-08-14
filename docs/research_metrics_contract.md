# Research Metrics Contract

Status: `proxy`

G011 adds a dossier-adjacent research appendix, not a replacement for the executive Scenario Dossier.

Generate:

```bash
PYTHONPATH=src python3 scripts/generate_research_metrics.py --dossier reports/dossiers/abay-signal-retiming/dossier.json --portfolio-matrix reports/portfolio/month1/kpi_matrix.csv --out reports/research_metrics/abay-signal-retiming
```

Outputs:

- `reports/research_metrics/abay-signal-retiming/research_metrics.json`
- `reports/research_metrics/abay-signal-retiming/dossier_appendix.md`
- `reports/research_metrics/abay-signal-retiming/research_visual.html`

Selected metrics:

| Metric | Formula | Official-facing reason |
|---|---|---|
| `reliability_index` | `bus_reliability_proxy.measure - max(queue_load_proxy.delta, 0) * 10` | Shows predictable corridor/public transport operation. |
| `emissions_proxy` | G004 CO2/NOx vehicle-hour proxies | Adds environmental appendix evidence. |
| `person_hours_sensitivity_interval` | `person_hours_saved.measure * [0.85, 1.0, 1.15]` | Makes uncertainty visible before observed validation. |
| `scenario_kpi_matrix` | `max(portfolio matrix person_hours_saved)` | Compares dossier scenario against alternatives. |
| `network_hour_heatmap` | hourly measure `congestion_index` values | Provides an exportable publication visual. |

All metrics are `proxy` and remain appendix evidence until observed validation, Monte Carlo uncertainty, and calibrated emissions inputs are attached.
