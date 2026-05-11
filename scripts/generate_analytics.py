import json
import random
import os
import csv
from datetime import datetime, timedelta

def generate_analytics():
    # Attempt to read trips.json for base data if available, or generate synthetic
    try:
        with open(os.path.join("data", "trips.json"), "r") as f:
            trips_data = json.load(f)
            num_trips = len(trips_data.get("trips", []))
    except Exception:
        num_trips = 150

    try:
        with open(os.path.join("data", "traffic_data.json"), "r") as f:
            traffic_data = json.load(f)
            roads = traffic_data.get("roads", [])
    except Exception:
        roads = [{"id": f"road_{i}", "density": random.uniform(0, 1)} for i in range(100)]

    # 1. Overall Analytics
    # Average time in trips: e.g. 15-45 minutes
    average_trip_time_s = random.uniform(900, 2700)

    # Calculate congestion index (0-100%)
    avg_density = sum(r.get("density", 0) for r in roads) / len(roads) if roads else 0
    congestion_index = round(avg_density * 100, 2)

    # Node throughput (top 10 nodes for dashboard)
    node_throughput = []
    for i in range(10):
        node_throughput.append({
            "node_id": f"node_{random.randint(1000, 9999)}",
            "vehicles_per_hour": random.randint(500, 3000),
            "status": random.choice(["normal", "heavy", "congested"])
        })

    # 2. Time-of-day charts
    # 24 hour breakdown
    time_series = []
    for hour in range(24):
        # Base traffic curve: peak at 8-9 and 18-19
        if hour in (8, 9, 17, 18, 19):
            base_idx = random.uniform(70, 95)
        elif hour in range(1, 6):
            base_idx = random.uniform(5, 20)
        else:
            base_idx = random.uniform(30, 60)

        time_series.append({
            "hour": f"{hour:02d}:00",
            "congestion_index": round(base_idx, 2),
            "avg_speed_kph": round(max(10, 60 - (base_idx / 2)), 1)
        })

    # 3. ML Forecast (Next hour prediction)
    # Simple mock forecast
    current_hour = datetime.now().hour
    current_idx = next((t["congestion_index"] for t in time_series if t["hour"] == f"{current_hour:02d}:00"), 50)

    forecasts = []
    for i in range(1, 4):
        future_idx = max(0, min(100, current_idx + random.uniform(-10, 15)))
        forecasts.append({
            "offset_hours": i,
            "predicted_congestion": round(future_idx, 2),
            "confidence": round(random.uniform(0.7, 0.95), 2)
        })
        current_idx = future_idx

    # Data Contract
    analytics_data = {
        "summary": {
            "average_trip_time_seconds": round(average_trip_time_s, 2),
            "congestion_index": congestion_index,
            "total_active_vehicles": num_trips * random.randint(10, 50),
        },
        "node_throughput": sorted(node_throughput, key=lambda x: x["vehicles_per_hour"], reverse=True),
        "time_series": time_series,
        "ml_forecast": forecasts
    }

    # Save JSON
    os.makedirs("data", exist_ok=True)
    json_path = os.path.join("data", "analytics.json")
    with open(json_path, "w") as f:
        json.dump(analytics_data, f, indent=2)

    # Save CSV Report
    csv_path = os.path.join("data", "analytics_report.csv")
    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Hour", "Congestion_Index", "Avg_Speed_kph", "Predicted_Next_Hour"])
        for idx, entry in enumerate(time_series):
            # mock predicted next hour
            next_val = time_series[(idx + 1) % 24]["congestion_index"]
            writer.writerow([
                entry["hour"],
                entry["congestion_index"],
                entry["avg_speed_kph"],
                next_val
            ])

    print(f"Analytics data generated successfully at {json_path} and {csv_path}")

if __name__ == "__main__":
    generate_analytics()
