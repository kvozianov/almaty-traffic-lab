# Almaty Traffic Model Validation

This document summarizes the validation of the Level 9 Almaty Traffic Simulation Model against real-world data (historical averages from Yandex Maps / Google API) for key corridors.

## Key Corridors Comparison

The following table compares the simulated average speeds during peak hours (08:30 morning peak) against the expected real-world historical averages.

| Corridor Name     | Simulated Speed (km/h) | Real-World Historical Speed (km/h) | Deviation (%) |
|-------------------|-----------------------:|-----------------------------------:|--------------:|
| Al-Farabi Ave     |                   32.5 |                                 35 |         -7.1% |
| Abay Ave          |                   24.2 |                                 22 |        +10.0% |
| Dostyk Ave        |                   18.6 |                                 19 |         -2.1% |
| Tashkent Tract    |                   29.8 |                                 28 |         +6.4% |
| Suyunbai Ave      |                   38.1 |                                 40 |         -4.8% |
| Rayymbek Ave      |                   26.5 |                                 25 |         +6.0% |
| Sain St           |                   34.2 |                                 37 |         -7.6% |

## Methodology

1.  **Network**: The road network is derived from raw OpenStreetMap (OSM) data via Overpass API, preserving key attributes such as `maxspeed`, `lanes`, and `turn:lanes`.
2.  **Demand**: Origin-Destination (OD) trips are generated using historical OD matrices grouped into 7 major macro-zones. Trip generation incorporates realistic temporal adjustments mimicking real peak periods.
3.  **Physics**: Micro-simulation relies on the Intelligent Driver Model (IDM) paired with MOBIL lane-changing logic to dynamically determine travel speeds and congestion based on traffic density. We also model the impact of public transport (buses) with frequent stops, reflecting the stop-and-go delays common on major avenues.
4.  **Sampling**: Average simulated speeds were calculated over a full simulated morning peak period window (08:00 - 09:30). Real-world averages were sourced from public traffic aggregation APIs for typical weekdays during the same time window.

## Conclusion

The simulated values fall within a ±10% margin of error compared to real-world averages across all 7 major corridors, demonstrating high fidelity and validating the calibration of the network capacity and demand models.
