from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Protocol

from .models import Vehicle
from .network import CityGraph


BEHAVIORS = ("normal", "avoid_congestion", "aggressive_reroute", "cautious")


@dataclass(slots=True)
class PolicyDecision:
    start_node: str
    destination_node: str
    behavior: str
    spawn_road_id: str
    spawn_ratio: float


class AIDriverPolicy(Protocol):
    def choose_trip(
        self,
        graph: CityGraph,
        rng: random.Random,
        road_loads: dict[str, float],
        minute_of_day: int,
    ) -> PolicyDecision:
        ...


class HeuristicPolicy:
    def choose_trip(
        self,
        graph: CityGraph,
        rng: random.Random,
        road_loads: dict[str, float],
        minute_of_day: int,
    ) -> PolicyDecision:
        roads = [road for road in graph.roads.values() if road.is_open and graph.outgoing.get(road.end_node)]
        if not roads:
            raise ValueError("No routable roads are available for policy selection")
        if 7 * 60 <= minute_of_day <= 10 * 60 or 17 * 60 <= minute_of_day <= 20 * 60:
            behavior_weights = [0.35, 0.35, 0.2, 0.1]
        else:
            behavior_weights = [0.55, 0.2, 0.1, 0.15]
        behavior = rng.choices(BEHAVIORS, weights=behavior_weights, k=1)[0]
        start_road = rng.choice(roads)
        candidates = [road for road in roads if road.end_node != start_road.start_node]
        if behavior == "avoid_congestion":
            candidates.sort(key=lambda road: road_loads.get(road.road_id, 0.0))
            destination_road = rng.choice(candidates[: max(3, len(candidates) // 5)])
        elif behavior == "aggressive_reroute":
            candidates.sort(key=lambda road: road.length_m, reverse=True)
            destination_road = rng.choice(candidates[: max(3, len(candidates) // 4)])
        else:
            destination_road = rng.choice(candidates)
        return PolicyDecision(
            start_node=start_road.end_node,
            destination_node=destination_road.start_node,
            behavior=behavior,
            spawn_road_id=start_road.road_id,
            spawn_ratio=rng.random(),
        )


class LlmPolicyProvider:
    def choose_trip(
        self,
        graph: CityGraph,
        rng: random.Random,
        road_loads: dict[str, float],
        minute_of_day: int,
    ) -> PolicyDecision:
        # Placeholder for future OpenAI-compatible policy integration.
        return HeuristicPolicy().choose_trip(graph, rng, road_loads, minute_of_day)


def build_policy(policy_name: str) -> AIDriverPolicy:
    if policy_name == "llm":
        return LlmPolicyProvider()
    return HeuristicPolicy()


def vehicle_from_decision(vehicle_id: str, decision: PolicyDecision, departure_time_s: float) -> Vehicle:
    return Vehicle(
        vehicle_id=vehicle_id,
        start_node=decision.start_node,
        destination_node=decision.destination_node,
        departure_time_s=departure_time_s,
        behavior=decision.behavior,
        spawn_road_id=decision.spawn_road_id,
        spawn_ratio=decision.spawn_ratio,
    )
