# Analytics Data Contract (Level 4)

## `GET /api/analytics`

Returns a strict JSON payload with the following structure:

```json
{
  "summary": {
    "average_trip_time_seconds": 1200.5,
    "congestion_index": 78.5,
    "total_active_vehicles": 1500
  },
  "node_throughput": [
    {
      "node_id": "node_1234",
      "vehicles_per_hour": 2500,
      "status": "congested"
    }
  ],
  "time_series": [
    {
      "hour": "08:00",
      "congestion_index": 85.2,
      "avg_speed_kph": 15.5
    }
  ],
  "ml_forecast": [
    {
      "offset_hours": 1,
      "predicted_congestion": 88.0,
      "confidence": 0.85
    }
  ]
}
```

- `summary.average_trip_time_seconds` (float): Average duration of active trips.
- `summary.congestion_index` (float): Overall city congestion level (0-100).
- `summary.total_active_vehicles` (int): Number of currently simulated vehicles.
- `node_throughput` (array): List of the most congested/busiest intersections. Status must be one of `normal`, `heavy`, or `congested`.
- `time_series` (array): 24-hour breakdown of historical or current simulated day. `hour` is formatted as `HH:00`.
- `ml_forecast` (array): Predictive congestion levels for the upcoming hours. `offset_hours` starts at 1 for the next hour.

## `GET /api/analytics/export`

Returns a CSV file with the `text/csv` content type containing the `time_series` and predicted next-hour data:

```csv
Hour,Congestion_Index,Avg_Speed_kph,Predicted_Next_Hour
08:00,85.2,15.5,88.0
```
