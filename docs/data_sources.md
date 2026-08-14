# Almaty Mobility Data Sources And Legal Posture

Status: `demo`

This note separates public, cached, demo, proxy, and future municipal/commercial sources so the platform does not imply live city data before evidence exists.

## Source Classes

| Source Class | Examples | Current Claim Level | Current Evidence | Legal/Operational Rule |
|---|---|---|---|---|
| Cached road geometry | `data/almaty_roads.geojson`, `cache/graphs/` | real-data | imported/cached local files | record source, freshness, and refresh command before stronger claims |
| Demo traffic density | `data/traffic_data.json` | demo | local prototype file | do not call live traffic |
| Generated analytics | `data/analytics_normal_abay.json`, `reports/portfolio/` | proxy | deterministic/proxy formulas | expose formulas and limitations |
| Calibration assumptions | `data/calibration/almaty_calibration_layer.json` | proxy | local layer and validation notes | attach observed-vs-sim rows per run before `calibrated` claims |
| Manual incident input | `data/operations/sample_incident_abay.json` | proxy | G007 sample incident | replace with verified incident feed before real-data claims |
| Commercial display/API layers | Yandex, 2GIS | planned/demo | provider status stubs | do not store raw data unless terms allow |
| Municipal feeds | Sergek, Onay, cameras, counters | planned | none | keep raw data in city-controlled storage; require DPA/access agreement |

## Provider Status Requirement

Every future provider should expose:

- provider ID and owner
- source type and legal mode
- availability
- freshness / last refresh timestamp
- raw-data retention permission
- claim label
- limitations

## Current Provider Registry

Generated artifacts:

- `reports/data_sources/provider_registry.json`
- `reports/data_sources/roads_geojson_provider_status.json`

API surfaces:

- `GET /api/data-sources`
- `GET /api/roads` with top-level `providerStatus`

Current `real-data` source:

- `roads-geojson`
- provider: OpenStreetMap/OSMnx import snapshot
- feature count: 2,417 at the 2026-06-05 refresh metadata generation
- claim boundary: cached/imported road geometry, not live traffic

## Data Residency Rule

The procurement posture is local/on-prem or Kazakhstan-approved hosting. Raw municipal feeds should remain in city-controlled storage. Dossiers should prefer derived indicators and source fingerprints unless agreements permit raw-data export.
