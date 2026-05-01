from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from traffic_sim.ai_policy import build_policy
from traffic_sim.calibration import load_calibration_layer, match_calibration_to_graph
from traffic_sim.demand import generate_vehicle_demand
from traffic_sim.graph_cache import load_graph_json, save_graph_json
from traffic_sim.network import build_demo_city_graph
from traffic_sim.road_attributes import normalize_road_attributes, parse_lanes, parse_maxspeed
from traffic_sim.scenarios import close_road_for_repair, reduce_capacity
from traffic_sim.simulation import TrafficSimulation
from traffic_sim.time_profiles import load_time_profile, parse_hhmm
from traffic_sim.timeline import generate_random_events, is_window_active
from traffic_sim.traffic_providers import CsvTrafficProvider, SyntheticTrafficProvider
from traffic_sim.web_app import app
from traffic_sim.zones import build_zone_index, choose_od_zones, load_od_matrix, load_zones


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
        self.assertEqual(len(loaded.signals), len(graph.signals))

    def test_calibration_layer_matches_demo_graph(self) -> None:
        graph = build_demo_city_graph()
        matched = match_calibration_to_graph(graph)
        self.assertEqual(len(load_calibration_layer()["segments"]), 50)
        self.assertGreater(matched["summary"]["segmentsMatched"], 0)
        self.assertGreater(matched["summary"]["intersectionsMatched"], 0)

    def test_road_attribute_parsers_support_osm_and_fallbacks(self) -> None:
        self.assertEqual(parse_maxspeed("50 km/h", "primary"), (50.0, "osm"))
        self.assertEqual(parse_maxspeed(["80", "60"], "primary"), (60.0, "osm"))
        self.assertEqual(parse_maxspeed("RU:urban", "primary"), (60.0, "osm"))
        self.assertEqual(parse_maxspeed("signals", "residential"), (40.0, "maxspeed_fallback"))
        self.assertEqual(parse_lanes("1;2", "primary"), (2, "osm"))
        self.assertEqual(parse_lanes(None, "trunk"), (3, "lanes_fallback"))

    def test_capacity_depends_on_lanes_and_road_class(self) -> None:
        one_lane = normalize_road_attributes({"highway": "primary", "maxspeed": "60", "lanes": "1"})
        three_lane = normalize_road_attributes({"highway": "primary", "maxspeed": "60", "lanes": "3"})
        self.assertEqual(one_lane.capacity, 24)
        self.assertEqual(three_lane.capacity, 72)

    def test_demand_generator_creates_valid_departures(self) -> None:
        graph = build_demo_city_graph()
        vehicles = generate_vehicle_demand(graph, vehicle_count=12, seed=4, horizon_s=600)
        self.assertEqual(len(vehicles), 12)
        self.assertTrue(all(vehicle.departure_time_s >= 0 for vehicle in vehicles))
        self.assertEqual(vehicles, sorted(vehicles, key=lambda vehicle: vehicle.departure_time_s))
        self.assertTrue(all(vehicle.spawn_road_id for vehicle in vehicles))
        self.assertTrue(all(vehicle.behavior in {"normal", "avoid_congestion", "aggressive_reroute", "cautious"} for vehicle in vehicles))

    def test_zone_loader_and_od_demand_create_valid_zone_trips(self) -> None:
        graph = build_demo_city_graph()
        zones = load_zones()
        od_matrix = load_od_matrix()
        index = build_zone_index(graph, zones, limit=8)
        self.assertEqual(len(zones), 7)
        self.assertTrue(all(index[zone.zone_id]["roads"] for zone in zones))
        import random

        origin, destination = choose_od_zones(zones, random.Random(7), parse_hhmm("08:00"), preset="morning_peak", od_matrix=od_matrix)
        self.assertIn(origin.zone_id, od_matrix)
        self.assertIn(destination.zone_id, od_matrix[origin.zone_id])
        vehicles = generate_vehicle_demand(
            graph,
            vehicle_count=8,
            seed=12,
            horizon_s=300,
            minute_of_day=parse_hhmm("17:00"),
            demand_mode="od_zones",
            zones=zones,
            time_preset="evening_peak",
        )
        self.assertEqual(len(vehicles), 8)
        self.assertTrue(all(vehicle.origin_zone_id for vehicle in vehicles))
        self.assertTrue(all(vehicle.destination_zone_id for vehicle in vehicles))
        self.assertTrue(all(vehicle.origin_zone_id != vehicle.destination_zone_id for vehicle in vehicles))

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

    def test_timeline_window_and_random_events_are_deterministic(self) -> None:
        graph = build_demo_city_graph()
        self.assertTrue(is_window_active("17:10", 40, parse_hhmm("17:20")))
        self.assertFalse(is_window_active("17:10", 40, parse_hhmm("18:10")))
        first = generate_random_events(graph, seed=4, duration_minutes=90, start_time="17:00")
        second = generate_random_events(graph, seed=4, duration_minutes=90, start_time="17:00")
        self.assertEqual([event.to_payload() for event in first], [event.to_payload() for event in second])

    def test_reroute_interval_avoids_blocked_upcoming_road(self) -> None:
        graph = build_demo_city_graph()
        vehicle = generate_vehicle_demand(graph, vehicle_count=1, seed=2, horizon_s=0)[0]
        vehicle.start_node = "west"
        vehicle.destination_node = "east"
        vehicle.spawn_road_id = "abay_ab"
        vehicle.departure_time_s = 0
        vehicle.behavior = "avoid_congestion"
        sim = TrafficSimulation(graph, tick_seconds=10, reroute_interval_ticks=1)
        sim.add_vehicle(vehicle)
        graph.roads["satpayev_ab"].is_open = False
        sim.step(1)
        self.assertGreaterEqual(sim.vehicles[vehicle.vehicle_id].reroutes, 0)
        self.assertNotIn("satpayev_ab", sim.vehicles[vehicle.vehicle_id].route_roads[1:])

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

    def test_signal_delay_increases_travel_time(self) -> None:
        graph = build_demo_city_graph()
        road = graph.roads["abay_ab"]
        before = road.travel_time_s()
        road.signal_delay_s += 30
        self.assertGreater(road.travel_time_s(), before)

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
        self.assertIn("speedSource", road.json()["road"])
        self.assertIn("lanesSource", road.json()["road"])
        signals = client.get("/api/signals?preset_id=demo")
        self.assertEqual(signals.status_code, 200)
        self.assertGreaterEqual(len(signals.json()["signals"]), 1)
        imported = client.post(
            "/api/traffic/import",
            json={"provider": "csv", "path": "data/traffic_profiles/sample_almaty.csv"},
        )
        self.assertEqual(imported.status_code, 200)
        stats = client.get("/api/statistics/road/al_farabi?provider_id=csv")
        self.assertEqual(stats.status_code, 200)
        self.assertGreater(len(stats.json()["observations"]), 0)

    def test_fastapi_zones_analytics_and_report_export(self) -> None:
        client = TestClient(app)
        self.assertEqual(client.get("/api/zones").status_code, 200)
        self.assertEqual(len(client.get("/api/zones").json()["zones"]), 7)
        self.assertEqual(client.get("/api/time-presets").status_code, 200)
        presets = client.get("/api/scenario-presets")
        self.assertEqual(presets.status_code, 200)
        self.assertGreaterEqual(len(presets.json()["presets"]), 3)
        calibration = client.get("/api/calibration-layer?preset_id=demo")
        self.assertEqual(calibration.status_code, 200)
        self.assertGreater(calibration.json()["layer"]["summary"]["segmentsMatched"], 0)
        response = client.post(
            "/api/preview",
            json={
                "preset_id": "demo",
                "vehicles": 60,
                "steps": 30,
                "seed": 6,
                "demand_mode": "od_zones",
                "random_events": True,
                "events": [{"type": "accident", "road_id": "abay_ab", "start_time": "17:00", "duration_minutes": 30}],
            },
        )
        self.assertEqual(response.status_code, 200)
        run_id = response.json()["id"]
        analytics = client.get(f"/api/simulations/{run_id}/analytics")
        self.assertEqual(analytics.status_code, 200)
        self.assertIn("topRoads", analytics.json()["analytics"])
        self.assertIn("odPairs", analytics.json()["analytics"])
        self.assertIn("routeCoverage", analytics.json()["analytics"])
        self.assertIn("calibration", analytics.json()["analytics"])
        report = client.get(f"/api/simulations/{run_id}/export/report")
        self.assertEqual(report.status_code, 200)
        self.assertTrue(Path(report.json()["path"]).exists())

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
        self.assertTrue(all("routeRoadIds" in vehicle for vehicle in payload["proceduralVehicles"]))
        self.assertTrue(any(road["signalDelayS"] > 0 for road in payload["roads"]))
        used_roads = {vehicle["roadId"] for vehicle in payload["proceduralVehicles"]}
        route_lengths = [len(vehicle.get("routeRoadIds", [])) for vehicle in payload["proceduralVehicles"]]
        self.assertGreater(len(used_roads), 20)
        self.assertGreater(sum(route_lengths) / len(route_lengths), 3.0)

    def test_od_preview_contains_graph_routes_between_zones(self) -> None:
        client = TestClient(app)
        response = client.post(
            "/api/preview",
            json={"preset_id": "demo", "vehicles": 80, "steps": 20, "seed": 13, "demand_mode": "od_zones"},
        )
        self.assertEqual(response.status_code, 200)
        run_id = response.json()["id"]
        payload = client.get(f"/api/simulations/{run_id}/frames").json()
        routed = [vehicle for vehicle in payload["proceduralVehicles"] if vehicle.get("originZone") and vehicle.get("destinationZone")]
        unique_starts = {vehicle["roadId"] for vehicle in payload["proceduralVehicles"]}
        self.assertGreater(len(routed), 0)
        self.assertTrue(any(len(vehicle.get("routeRoadIds", [])) > 1 for vehicle in routed))
        self.assertGreater(len(unique_starts), 12)
        self.assertGreater(sum(len(vehicle.get("routeRoadIds", [])) for vehicle in routed) / len(routed), 2.5)

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
