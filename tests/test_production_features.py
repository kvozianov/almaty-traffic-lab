from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from traffic_sim.ai_policy import build_policy
from traffic_sim.demand import generate_vehicle_demand
from traffic_sim.graph_cache import load_graph_json, save_graph_json
from traffic_sim.network import build_demo_city_graph
from traffic_sim.scenarios import close_road_for_repair, reduce_capacity
from traffic_sim.simulation import TrafficSimulation
from traffic_sim.time_profiles import load_time_profile, parse_hhmm
from traffic_sim.traffic_providers import CsvTrafficProvider, SyntheticTrafficProvider
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
        self.assertEqual(loaded.roads["abay_ab"].lanes, graph.roads["abay_ab"].lanes)
        self.assertEqual(loaded.roads["abay_ab"].road_class, graph.roads["abay_ab"].road_class)

    def test_demand_generator_creates_valid_departures(self) -> None:
        graph = build_demo_city_graph()
        vehicles = generate_vehicle_demand(graph, vehicle_count=12, seed=4, horizon_s=600)
        self.assertEqual(len(vehicles), 12)
        self.assertTrue(all(vehicle.departure_time_s >= 0 for vehicle in vehicles))
        self.assertEqual(vehicles, sorted(vehicles, key=lambda vehicle: vehicle.departure_time_s))
        self.assertTrue(all(vehicle.spawn_road_id for vehicle in vehicles))
        self.assertTrue(all(vehicle.behavior in {"normal", "avoid_congestion", "aggressive_reroute", "cautious"} for vehicle in vehicles))

    def test_random_road_spawn_places_vehicle_on_spawn_road(self) -> None:
        graph = build_demo_city_graph()
        vehicle = generate_vehicle_demand(graph, vehicle_count=1, seed=11, horizon_s=0)[0]
        sim = TrafficSimulation(graph, tick_seconds=10)
        sim.add_vehicle(vehicle)
        spawned = sim.vehicles[vehicle.vehicle_id]
        self.assertEqual(spawned.current_road_id, vehicle.spawn_road_id)
        self.assertGreater(spawned.progress_m, 0)

    def test_heuristic_policy_returns_valid_trip(self) -> None:
        graph = build_demo_city_graph()
        import random

        decision = build_policy("heuristic").choose_trip(graph, random.Random(5), road_loads={}, minute_of_day=parse_hhmm("17:00"))
        self.assertIn(decision.start_node, graph.nodes)
        self.assertIn(decision.destination_node, graph.nodes)
        self.assertIn(decision.spawn_road_id, graph.roads)

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

    def test_time_profile_slows_named_corridor_at_evening_peak(self) -> None:
        graph = build_demo_city_graph()
        road = graph.roads["abay_ab"]
        road.metadata["name"] = "Al-Farabi"
        profile = load_time_profile()
        evening = profile.speed_multiplier_for_road(road, parse_hhmm("17:00"))
        night = profile.speed_multiplier_for_road(road, parse_hhmm("23:00"))
        self.assertLess(evening, night)

    def test_capacity_reduction_changes_effective_capacity(self) -> None:
        graph = build_demo_city_graph()
        before = graph.roads["abay_ab"].effective_capacity()
        reduce_capacity(graph, "abay_ab", 0.25)
        self.assertLess(graph.roads["abay_ab"].effective_capacity(), before)

    def test_traffic_providers_return_local_statuses(self) -> None:
        synthetic = SyntheticTrafficProvider()
        self.assertTrue(synthetic.status()["available"])
        self.assertGreater(len(synthetic.observations_for_road("Al-Farabi")), 0)
        csv_provider = CsvTrafficProvider("data/traffic_profiles/sample_almaty.csv")
        self.assertTrue(csv_provider.status()["available"])

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

    def test_fastapi_new_research_endpoints(self) -> None:
        client = TestClient(app)
        self.assertEqual(client.get("/api/time-profiles").status_code, 200)
        providers = client.get("/api/traffic/providers")
        self.assertEqual(providers.status_code, 200)
        self.assertIn("synthetic", {provider["id"] for provider in providers.json()["providers"]})
        decisions = client.post(
            "/api/policies/select-destinations",
            json={"preset_id": "demo", "vehicles": 3, "manual_time": "17:00"},
        )
        self.assertEqual(decisions.status_code, 200)
        self.assertEqual(len(decisions.json()["decisions"]), 3)
        road = client.get("/api/roads/abay_ab?preset_id=demo")
        self.assertEqual(road.status_code, 200)
        self.assertEqual(road.json()["road"]["id"], "abay_ab")
        imported = client.post(
            "/api/traffic/import",
            json={"provider": "csv", "path": "data/traffic_profiles/sample_almaty.csv"},
        )
        self.assertEqual(imported.status_code, 200)
        stats = client.get("/api/statistics/road/al_farabi?provider_id=csv")
        self.assertEqual(stats.status_code, 200)
        self.assertGreater(len(stats.json()["observations"]), 0)

    def test_preview_uses_procedural_vehicle_stream_for_mass_mode(self) -> None:
        client = TestClient(app)
        response = client.post(
            "/api/preview",
            json={"preset_id": "demo", "vehicles": 250, "steps": 20, "seed": 9},
        )
        self.assertEqual(response.status_code, 200)
        run_id = response.json()["id"]
        frames = client.get(f"/api/simulations/{run_id}/frames")
        self.assertEqual(frames.status_code, 200)
        payload = frames.json()
        self.assertTrue(payload["procedural"])
        self.assertEqual(len(payload["proceduralVehicles"]), 250)
        self.assertTrue(response.json()["procedural"])
        self.assertTrue(all("nextRoadId" in road for road in payload["roads"]))
        self.assertTrue(all(vehicle["speed"] > 0 for vehicle in payload["proceduralVehicles"]))
        self.assertTrue(all(vehicle["speedKph"] > 0 for vehicle in payload["proceduralVehicles"]))
        used_roads = {vehicle["roadId"] for vehicle in payload["proceduralVehicles"]}
        self.assertGreater(len(used_roads), 20)

    def test_preview_scenario_changes_road_speed_and_load(self) -> None:
        client = TestClient(app)
        response = client.post(
            "/api/preview",
            json={
                "preset_id": "demo",
                "vehicles": 80,
                "steps": 20,
                "seed": 9,
                "scenario": {"type": "accident", "road_id": "abay_ab", "speed_factor": 0.2, "capacity_factor": 0.2},
            },
        )
        self.assertEqual(response.status_code, 200)
        run_id = response.json()["id"]
        frames = client.get(f"/api/simulations/{run_id}/frames").json()
        road = next(item for item in frames["roads"] if item["id"] == "abay_ab")
        self.assertEqual(road["scenario"], "accident")
        self.assertLess(road["speedModifier"], 1.0)
        self.assertGreaterEqual(road["load"], 1.0)


if __name__ == "__main__":
    unittest.main()
