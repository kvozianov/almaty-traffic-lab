import json
import random
import os
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from traffic_sim.executive_kpis import build_executive_kpi_block


def generate_analytics(pattern="normal", closed_streets="", seed=7):
    rng = random.Random(f"{pattern}:{closed_streets}:{seed}")
    deterministic_synthetic = os.getenv("TRAFFIC_SIM_REPRODUCIBLE_SYNTHETIC") == "1"

    if deterministic_synthetic:
        num_trips = 150
    else:
        fileName = f"trips_{pattern}"
        if closed_streets:
            fileName += "_" + "".join(c if c.isalnum() else "_" for c in closed_streets)
        fileName += ".json"
        try:
            with open(os.path.join("data", fileName), "r", encoding="utf-8") as f:
                trips_data = json.load(f)
            num_trips = len(trips_data.get("trips", []))
        except (FileNotFoundError, json.JSONDecodeError):
            num_trips = 150

    if deterministic_synthetic:
        roads = [{"id": f"road_{i}", "density": rng.uniform(0, 1)} for i in range(100)]
    else:
        try:
            with open(os.path.join("data", "traffic_data.json"), "r", encoding="utf-8") as f:
                traffic_data = json.load(f)
            roads = traffic_data.get("roads", [])
        except (FileNotFoundError, json.JSONDecodeError):
            roads = [{"id": f"road_{i}", "density": rng.uniform(0, 1)} for i in range(100)]

    # 1. Overall Analytics
    # Average time in trips: e.g. 15-45 minutes
    average_trip_time_s = rng.uniform(900, 2700)

    # Calculate congestion index (0-100%)
    avg_density = sum(r.get("density", 0) for r in roads) / len(roads) if roads else 0
    congestion_index = round(avg_density * 100, 2)

    # Node throughput (top 10 nodes for dashboard)
    node_throughput = []
    for i in range(10):
        node_throughput.append({
            "node_id": f"node_{rng.randint(1000, 9999)}",
            "vehicles_per_hour": rng.randint(500, 3000),
            "status": rng.choice(["normal", "heavy", "congested"])
        })

    # 2. Time-of-day charts
    # 24 hour breakdown
    time_series = []
    for hour in range(24):
        if pattern == "night":
            base_idx = rng.uniform(5, 15)
        elif pattern == "weekend":
            # Peak slightly later in the day, smoother
            if hour in range(11, 16):
                base_idx = rng.uniform(50, 75)
            elif hour in range(1, 6):
                base_idx = rng.uniform(5, 20)
            else:
                base_idx = rng.uniform(25, 45)
        else:
            # Base traffic curve: peak at 8-9 and 18-19
            if hour in (8, 9, 17, 18, 19):
                base_idx = rng.uniform(70, 95)
            elif hour in range(1, 6):
                base_idx = rng.uniform(5, 20)
            else:
                base_idx = rng.uniform(30, 60)

        # closed_streets penalize congestion everywhere
        if closed_streets:
            base_idx = min(100, base_idx * 1.2)

        time_series.append({
            "hour": f"{hour:02d}:00",
            "congestion_index": round(base_idx, 2),
            "avg_speed_kph": round(max(10, 60 - (base_idx / 2)), 1)
        })

    # 3. ML Forecast (Next hour prediction)
    # Simple mock forecast
    current_hour = 17
    current_idx = next((t["congestion_index"] for t in time_series if t["hour"] == f"{current_hour:02d}:00"), 50)

    forecasts = []
    for i in range(1, 4):
        future_idx = max(0, min(100, current_idx + rng.uniform(-10, 15)))
        forecasts.append({
            "offset_hours": i,
            "predicted_congestion": round(future_idx, 2),
            "confidence": round(rng.uniform(0.7, 0.95), 2)
        })
        current_idx = future_idx

    # Data Contract
    analytics_data = {
        "summary": {
            "average_trip_time_seconds": round(average_trip_time_s, 2),
            "congestion_index": congestion_index,
            "total_active_vehicles": num_trips * rng.randint(10, 50),
        },
        "node_throughput": sorted(node_throughput, key=lambda x: x["vehicles_per_hour"], reverse=True),
        "time_series": time_series,
        "ml_forecast": forecasts,
    }
    baseline_data = _load_baseline(pattern) if closed_streets else analytics_data
    analytics_data["executive_kpis"] = build_executive_kpi_block(
        baseline_data or analytics_data,
        analytics_data,
        claim_level="proxy",
    )

    # Save JSON
    os.makedirs("data", exist_ok=True)
    json_name = f"analytics_{pattern}"
    if closed_streets:
        json_name += "_" + "".join(c if c.isalnum() else "_" for c in closed_streets)
    json_path = os.path.join("data", f"{json_name}.json")

    with open(json_path, "w") as f:
        json.dump(analytics_data, f, indent=2)

    # Save CSV Report
    csv_path = os.path.join("data", f"{json_name}_report.csv")
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


def _load_baseline(pattern):
    path = os.path.join("data", f"analytics_{pattern}.json")
    try:
        with open(path, "r", encoding="utf-8") as file:
            return json.load(file)
    except FileNotFoundError:
        return None


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--pattern", type=str, choices=["normal", "night", "weekend"], default="normal")
    parser.add_argument("--closed_streets", type=str, default="")
    parser.add_argument("--seed", type=int, default=7)
    args, _ = parser.parse_known_args()

    generate_analytics(pattern=args.pattern, closed_streets=args.closed_streets, seed=args.seed)
