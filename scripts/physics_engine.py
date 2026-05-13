import sys
import os
import json
import math
import random
import uuid

# Ensure we can import from src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from traffic_sim.graph_cache import load_preset_graph

def haversine(lon1, lat1, lon2, lat2):
    R = 6371000  # Radius of earth in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c

def calculate_heading(lon1, lat1, lon2, lat2):
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_lambda = math.radians(lon2 - lon1)

    x = math.sin(delta_lambda) * math.cos(phi2)
    y = math.cos(phi1) * math.sin(phi2) - (math.sin(phi1) * math.cos(phi2) * math.cos(delta_lambda))

    initial_bearing = math.atan2(x, y)
    initial_bearing = math.degrees(initial_bearing)
    return (initial_bearing + 360) % 360

def interpolate_segment(geom, distance_m):
    # Returns (lon, lat, heading, segment_idx)
    if not geom or len(geom) < 2:
        return (0.0, 0.0, 0.0, 0)

    traversed = 0.0
    for j in range(len(geom) - 1):
        p1 = geom[j]
        p2 = geom[j+1]
        dist = haversine(p1[0], p1[1], p2[0], p2[1])
        if traversed + dist >= distance_m:
            ratio = (distance_m - traversed) / dist if dist > 0 else 0
            lon = p1[0] + ratio * (p2[0] - p1[0])
            lat = p1[1] + ratio * (p2[1] - p1[1])
            heading = calculate_heading(p1[0], p1[1], p2[0], p2[1])
            return (lon, lat, heading, j)
        traversed += dist

    # End of geom
    p1 = geom[-2]
    p2 = geom[-1]
    heading = calculate_heading(p1[0], p1[1], p2[0], p2[1])
    return (geom[-1][0], geom[-1][1], heading, len(geom)-2)

def offset_coord(lon, lat, heading, offset_m):
    R = 6371000
    # Offset is perpendicular to the heading
    heading_rad = math.radians(heading + 90)
    lat_rad = math.radians(lat)
    lon_rad = math.radians(lon)

    new_lat = math.asin(math.sin(lat_rad)*math.cos(offset_m/R) +
                        math.cos(lat_rad)*math.sin(offset_m/R)*math.cos(heading_rad))
    new_lon = lon_rad + math.atan2(math.sin(heading_rad)*math.sin(offset_m/R)*math.cos(lat_rad),
                                   math.cos(offset_m/R)-math.sin(lat_rad)*math.sin(new_lat))
    return [math.degrees(new_lon), math.degrees(new_lat)]


class Agent:
    def __init__(self, agent_id, route_roads, start_time):
        self.id = agent_id
        self.route_roads = route_roads
        self.start_time = start_time

        # Stochastic parameters
        # aggressiveness ~ N(1.0, 0.2)
        aggressiveness = max(0.5, min(1.5, random.gauss(1.0, 0.2)))

        # reaction_time ~ N(1.5, 0.3)
        self.T = max(0.5, random.gauss(1.5, 0.3)) / aggressiveness

        # desired_speed factor ~ N(1.0, 0.1)
        self.v_factor = max(0.6, min(1.4, random.gauss(1.0, 0.1))) * aggressiveness

        # IDM parameters
        self.a_max = 1.0 * aggressiveness  # max acceleration m/s^2
        self.b = 1.5 * aggressiveness      # comfortable deceleration m/s^2
        self.s0 = 2.0                      # minimum gap
        self.delta = 4                     # acceleration exponent

        # MOBIL parameters
        self.politeness = random.uniform(0.1, 0.5)
        self.a_thr = 0.2
        self.b_safe = 2.0

        # State
        self.active = False
        self.finished = False
        self.current_road_idx = 0
        self.pos = 0.0      # distance along current road
        self.v = 0.0        # current speed
        self.a = 0.0        # current acceleration
        self.lane = 0       # current lane

        self.trajectory = []

    def get_desired_speed(self, graph, road_id):
        road = graph.roads[road_id]
        v0 = (road.max_speed_kph * 1000 / 3600) * self.v_factor
        return v0

def idm_acceleration(v, v0, s, delta_v, a_max, b, s0, T):
    if s < 0.1:
        s = 0.1
    s_star = s0 + v * T + (v * delta_v) / (2 * math.sqrt(a_max * b))
    if s_star < s0:
        s_star = s0

    a = a_max * (1 - (v / v0)**self.delta - (s_star / s)**2) if 'self' in locals() else a_max * (1 - (v / v0)**4 - (s_star / s)**2)
    return max(-5.0, a) # limit max deceleration to -5 m/s^2 for realism

def get_road_geom_length(geom):
    if not geom or len(geom) < 2:
        return 0.1
    traversed = 0.0
    for j in range(len(geom) - 1):
        p1 = geom[j]
        p2 = geom[j+1]
        dist = haversine(p1[0], p1[1], p2[0], p2[1])
        traversed += dist
    return traversed

def run_physics_simulation():
    print("Loading graph...")
    graph = load_preset_graph("full_almaty_fast")

    num_agents = 50 # Small number of agents for demonstration
    nodes_list = list(graph.nodes.keys())

    agents = []

    # Pre-calculate road lengths from geometry to be accurate
    road_lengths = {}
    for r_id, r in graph.roads.items():
        geom_raw = r.metadata.get('geometry')
        geom = list(geom_raw.coords) if hasattr(geom_raw, 'coords') else geom_raw
        if geom:
            road_lengths[r_id] = get_road_geom_length(geom)
        else:
            road_lengths[r_id] = r.length_m

    print(f"Generating routes for {num_agents} agents...")
    for i in range(num_agents):
        start = random.choice(nodes_list)
        end = random.choice(nodes_list)
        while start == end:
            end = random.choice(nodes_list)

        try:
            path = graph.shortest_path(start, end, algorithm="astar")
            if not path.nodes or len(path.roads) < 1:
                continue
        except Exception:
            continue

        agent = Agent(str(i+1), path.roads, random.uniform(0, 10))
        agents.append(agent)

    print(f"Starting simulation for {len(agents)} agents...")

    dt = 0.5 # Simulation tick step (seconds)
    max_time = 300.0 # 5 minutes max simulation

    current_time = 0.0

    # Store agents by road
    road_agents = {r_id: [] for r_id in graph.roads.keys()}

    while current_time < max_time:
        active_count = 0

        # 1. Spawn agents
        for agent in agents:
            if not agent.active and not agent.finished and current_time >= agent.start_time:
                agent.active = True
                road_id = agent.route_roads[0]
                road_agents[road_id].append(agent)
                # Assign random lane based on road
                lanes = graph.roads[road_id].lanes
                agent.lane = random.randint(0, max(0, lanes - 1))

        # Sort agents on each road by position
        for r_id in road_agents:
            road_agents[r_id].sort(key=lambda x: x.pos, reverse=True)

        # 2. Update states
        for agent in agents:
            if not agent.active:
                continue

            active_count += 1

            road_id = agent.route_roads[agent.current_road_idx]
            road = graph.roads[road_id]
            road_length = road_lengths[road_id]
            lanes = road.lanes
            v0 = agent.get_desired_speed(graph, road_id)

            # Find leader in the same lane
            leader = None
            leader_dist = float('inf')

            my_idx = road_agents[road_id].index(agent)
            for j in range(my_idx - 1, -1, -1):
                other = road_agents[road_id][j]
                if other.lane == agent.lane:
                    leader = other
                    leader_dist = other.pos - agent.pos
                    break

            v = agent.v

            if leader:
                delta_v = v - leader.v
                s = leader_dist - 5.0 # Vehicle length
                a = idm_acceleration(v, v0, max(0.1, s), delta_v, agent.a_max, agent.b, agent.s0, agent.T)
            else:
                # Approach intersection / end of road
                dist_to_end = road_length - agent.pos

                # Check if it's the final road
                if agent.current_road_idx == len(agent.route_roads) - 1:
                    # Slow down to stop at destination
                    s = dist_to_end
                    a = idm_acceleration(v, v0, max(0.1, s), v, agent.a_max, agent.b, agent.s0, agent.T)
                else:
                    # Next road logic - Gap Acceptance
                    next_road_id = agent.route_roads[agent.current_road_idx + 1]
                    # Simplified Gap Acceptance: if there's someone at the start of next road, slow down
                    next_road_agents = road_agents.get(next_road_id, [])
                    next_road_leader = None
                    for other in next_road_agents:
                        if other.pos < 20.0 and other.lane == agent.lane:
                            next_road_leader = other
                            break

                    if next_road_leader:
                        s = dist_to_end + next_road_leader.pos - 5.0
                        delta_v = v - next_road_leader.v
                        a = idm_acceleration(v, v0, max(0.1, s), delta_v, agent.a_max, agent.b, agent.s0, agent.T)
                    else:
                        # Yield logic / Intersection delay
                        # Random chance of waiting at an intersection
                        # For simplicity, just use free flow if no leader on next road
                        a = idm_acceleration(v, v0, float('inf'), 0, agent.a_max, agent.b, agent.s0, agent.T)


            # MOBIL (Lane changing) - simple logic
            if lanes > 1 and leader and leader.v < v0 * 0.8 and agent.pos > 10.0 and (road_length - agent.pos) > 50.0:
                # Check other lane
                other_lane = (agent.lane + 1) % lanes
                safe_to_change = True

                # Check for vehicles in the other lane
                for other in road_agents[road_id]:
                    if other.lane == other_lane:
                        if abs(other.pos - agent.pos) < 15.0: # Too close
                            safe_to_change = False
                            break

                if safe_to_change:
                    agent.lane = other_lane


            # Update kinematics
            agent.a = a
            agent.v += a * dt
            if agent.v < 0:
                agent.v = 0
            agent.pos += agent.v * dt

            # Record trajectory
            geom_raw = road.metadata.get('geometry')
            geom = list(geom_raw.coords) if hasattr(geom_raw, 'coords') else geom_raw
            if geom:
                lon, lat, heading, _ = interpolate_segment(geom, agent.pos)

                # Lane offset
                if lanes > 1:
                    offset_m = (agent.lane - (lanes - 1) / 2) * 3.0 # 3m per lane
                    lon, lat = offset_coord(lon, lat, heading, offset_m)

                agent.trajectory.append({
                    "t": round(current_time, 2),
                    "coord": [lon, lat],
                    "v": round(agent.v, 2),
                    "a": round(agent.a, 2)
                })

            # Road transition
            if agent.pos >= road_length:
                road_agents[road_id].remove(agent)
                agent.current_road_idx += 1
                if agent.current_road_idx >= len(agent.route_roads):
                    agent.active = False
                    agent.finished = True
                else:
                    new_road_id = agent.route_roads[agent.current_road_idx]
                    agent.pos = agent.pos - road_length # carry over
                    agent.lane = min(agent.lane, graph.roads[new_road_id].lanes - 1)
                    road_agents[new_road_id].append(agent)

        current_time += dt

        if active_count == 0 and current_time > 10.0:
            # all finished or didn't spawn
            all_finished = all(a.finished for a in agents if a.start_time <= current_time)
            if all_finished:
                break

    print(f"Simulation finished. Time: {current_time:.1f}s")

    # Format output
    output_agents = []
    for a in agents:
        if a.trajectory:
            output_agents.append({
                "id": a.id,
                "trajectory": a.trajectory
            })

    output = {
        "agents": output_agents
    }

    out_file = os.path.join("data", "physics_trajectories.json")
    with open(out_file, "w") as f:
        json.dump(output, f)

    print(f"Physics trajectories saved to {out_file} (agents: {len(output_agents)})")

if __name__ == "__main__":
    run_physics_simulation()
