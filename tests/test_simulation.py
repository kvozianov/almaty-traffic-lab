from __future__ import annotations

import unittest

from traffic_sim.network import CityGraph
from traffic_sim.scenarios import apply_accident, close_road_for_repair
from traffic_sim.simulation import TrafficSimulation
from traffic_sim.visualization import record_frames


def build_small_graph() -> CityGraph:
    graph = CityGraph()
    for node_id, coords in {
        "A": (0.0, 0.0),
        "B": (1.0, 0.0),
        "C": (2.0, 0.0),
        "D": (1.0, 1.0),
    }.items():
        graph.add_node(node_id, *coords)

    graph.add_road("A_B", "A", "B", length_m=1000, max_speed_kph=50, capacity=20)
    graph.add_road("B_C", "B", "C", length_m=1000, max_speed_kph=50, capacity=20)
    graph.add_road("A_D", "A", "D", length_m=1200, max_speed_kph=30, capacity=10)
    graph.add_road("D_C", "D", "C", length_m=1200, max_speed_kph=30, capacity=10)
    return graph


class TrafficSimulationTests(unittest.TestCase):
    def test_shortest_path_prefers_faster_route(self) -> None:
        graph = build_small_graph()
        path = graph.shortest_path("A", "C", algorithm="astar")
        self.assertEqual(path.roads, ["A_B", "B_C"])

    def test_closed_road_forces_reroute(self) -> None:
        graph = build_small_graph()
        close_road_for_repair(graph, "B_C")
        path = graph.shortest_path("A", "C")
        self.assertEqual(path.roads, ["A_D", "D_C"])

    def test_accident_reduces_effective_capacity(self) -> None:
        graph = build_small_graph()
        road = graph.roads["A_B"]
        before = road.effective_capacity()
        apply_accident(graph, "A_B")
        after = road.effective_capacity()
        self.assertLess(after, before)

    def test_vehicle_arrives_after_enough_steps(self) -> None:
        graph = build_small_graph()
        sim = TrafficSimulation(graph, tick_seconds=30)
        sim.spawn_vehicle("car-1", "A", "C")
        sim.step(8)
        vehicle = sim.vehicles["car-1"]
        self.assertTrue(vehicle.is_arrived())

    def test_visualization_records_initial_and_step_frames(self) -> None:
        graph = build_small_graph()
        sim = TrafficSimulation(graph, tick_seconds=30)
        sim.spawn_vehicle("car-1", "A", "C")
        frames = record_frames(sim, 2)
        self.assertEqual(len(frames), 3)
        self.assertEqual(frames[0].tick, 0)
        self.assertEqual(frames[-1].tick, 2)


if __name__ == "__main__":
    unittest.main()
