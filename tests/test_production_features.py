from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from traffic_sim.demand import generate_vehicle_demand
from traffic_sim.graph_cache import load_graph_json, save_graph_json
from traffic_sim.network import build_demo_city_graph
from traffic_sim.scenarios import close_road_for_repair
from traffic_sim.simulation import TrafficSimulation
from traffic_sim.web_app import app


class ProductionFeatureTests(unittest.TestCase):
    def test_graph_cache_roundtrip_preserves_graph(self) -> None:
        graph = build_demo_city_graph()
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "graph.json"
            save_graph_json(graph, path)
            loaded = load_graph_json(path)
        self.assertEqual(len(loaded.nodes), len(graph.nodes))
        self.assertEqual(len(loaded.roads), len(graph.roads))
        self.assertEqual(loaded.road_geometry("abay_ab"), graph.road_geometry("abay_ab"))

    def test_demand_generator_creates_valid_departures(self) -> None:
        graph = build_demo_city_graph()
        vehicles = generate_vehicle_demand(graph, vehicle_count=12, seed=4, horizon_s=600)
        self.assertEqual(len(vehicles), 12)
        self.assertTrue(all(vehicle.departure_time_s >= 0 for vehicle in vehicles))
        self.assertEqual(vehicles, sorted(vehicles, key=lambda vehicle: vehicle.departure_time_s))

    def test_departures_and_queueing_do_not_overfill_road(self) -> None:
        graph = build_demo_city_graph()
        graph.roads["abay_ab"].capacity = 1
        sim = TrafficSimulation(graph, tick_seconds=10)
        for index in range(3):
            sim.spawn_vehicle(f"car-{index}", "west", "east")
        sim.step(1)
        self.assertLessEqual(len(sim.road_occupancy["abay_ab"]), graph.roads["abay_ab"].effective_capacity())

    def test_repair_scenario_changes_route(self) -> None:
        graph = build_demo_city_graph()
        before = graph.shortest_path("north", "south").roads
        close_road_for_repair(graph, "seifullin_ab")
        after = graph.shortest_path("north", "south").roads
        self.assertNotEqual(before, after)

    def test_fastapi_demo_run_returns_frames(self) -> None:
        client = TestClient(app)
        response = client.post(
            "/api/simulations",
            json={
                "preset_id": "demo",
                "vehicles": 10,
                "steps": 20,
                "seed": 3,
                "scenario": {"type": "accident"},
            },
        )
        self.assertEqual(response.status_code, 200)
        run_id = response.json()["id"]
        frames = client.get(f"/api/simulations/{run_id}/frames")
        self.assertEqual(frames.status_code, 200)
        self.assertEqual(len(frames.json()["frames"]), 21)


if __name__ == "__main__":
    unittest.main()
