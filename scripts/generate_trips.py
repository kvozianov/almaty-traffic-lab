import sys
import os
import random
import json
import math

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

from traffic_sim.zones import load_zones, load_od_matrix, build_zone_index, choose_od_zones

def generate_trips(num_trips=150, pattern="normal", closed_streets="", out_file=None):
    print("Loading graph...")
    graph = load_preset_graph("full_almaty_fast")

    if closed_streets:
        closed_list = [s.strip().lower() for s in closed_streets.split(",") if s.strip()]
        for road_id, road in graph.roads.items():
            name = str(road.metadata.get("name", "")).lower()
            if any(closed in name for closed in closed_list):
                road.is_open = False

    print("Loading OD zones and matrix...")
    zones = load_zones()
    od_matrix = load_od_matrix()
    zone_index = build_zone_index(graph, zones, limit=100)

    # Determine simulated minute of day to apply peak multipliers
    # Assume: 'morning' peak around 08:30, 'evening' peak around 18:30
    # For a general 'normal' pattern without specific time, we'll randomize time
    # but weight towards peaks to make it interesting.

    # Scale number of trips based on pattern peak multipliers
    if pattern == "normal":
        minute_of_day = random.choice([8*60+30, 18*60+30, 13*60]) # Morning, Evening, Lunch
    elif pattern == "night":
        minute_of_day = 2*60 # 02:00 AM
        num_trips = max(10, int(num_trips * 0.2)) # Fewer trips at night
    elif pattern == "weekend":
        minute_of_day = 14*60 # 14:00 PM
        num_trips = int(num_trips * 0.8) # Moderate trips on weekend
    else:
        minute_of_day = 12*60

    rng = random.Random()

    trips = []

    print(f"Generating {num_trips} trips for time {minute_of_day//60:02d}:{minute_of_day%60:02d}...")

    attempts = 0
    max_attempts = num_trips * 10

    while len(trips) < num_trips and attempts < max_attempts:
        attempts += 1

        try:
            origin_zone, dest_zone = choose_od_zones(zones, rng, minute_of_day, preset=pattern, od_matrix=od_matrix)
            origin_nodes = zone_index.get(origin_zone.zone_id, {}).get("nodes", [])
            dest_nodes = zone_index.get(dest_zone.zone_id, {}).get("nodes", [])

            if not origin_nodes or not dest_nodes:
                continue

            start = random.choice(origin_nodes)
            end = random.choice(dest_nodes)

            # Ensure start and end are different
            if start == end:
                continue
        except ValueError:
            # Fallback if zones fail
            nodes_list = list(graph.nodes.keys())
            start = random.choice(nodes_list)
            end = random.choice(nodes_list)
            while start == end:
                end = random.choice(nodes_list)


        agent_type = random.choices(["car", "truck", "bus"], weights=[0.8, 0.1, 0.1])[0]
        try:

            path = graph.shortest_path(start, end, algorithm="astar")

            if not path.nodes or len(path.nodes) < 2:
                continue

            coordinates = []
            timestamps = []

            current_time = 0.0

            # Start node
            start_node = graph.nodes[path.nodes[0]]
            coordinates.append([start_node.x, start_node.y])
            timestamps.append(round(current_time, 2))

            # Follow edges
            for road_id in path.roads:
                road = graph.roads[road_id]
                # End node of the road
                end_node_id = road.end_node
                end_node = graph.nodes[end_node_id]

                # Calculate time to traverse road
                # speed = distance / time => time = distance / speed
                speed_mps = (road.max_speed_kph * 1000) / 3600
                if pattern == "night":
                    speed_mps *= 1.2 # Less traffic, faster travel

                if agent_type == "truck":
                    speed_mps *= 0.8
                elif agent_type == "bus":
                    speed_mps *= 0.7
                if speed_mps <= 0:
                    speed_mps = 13.8 # 50km/h fallback

                time_s = road.length_m / speed_mps

                geom_raw = road.metadata.get('geometry')
                geom = list(geom_raw.coords) if hasattr(geom_raw, 'coords') else geom_raw

                if geom and len(geom) > 1:
                    segment_lengths = []
                    for j in range(len(geom) - 1):
                        p1 = geom[j]
                        p2 = geom[j+1]
                        dist = haversine(p1[0], p1[1], p2[0], p2[1])
                        segment_lengths.append(dist)

                    total_geom_length = sum(segment_lengths)
                    if total_geom_length > 0:
                        for j in range(1, len(geom)):
                            p = geom[j]
                            fraction = segment_lengths[j-1] / total_geom_length
                            segment_time = time_s * fraction
                            current_time += segment_time

                            # Add random minor delays to simulate yielding / pedestrian crossings
                            # We can trigger this roughly every few segments for realism
                            if random.random() < 0.05:
                                current_time += random.uniform(2.0, 5.0)
                            coordinates.append(list(p)) # ensure it's a list for json serialization
                            timestamps.append(round(current_time, 2))
                    else:
                        current_time += time_s
                        coordinates.append([end_node.x, end_node.y])
                        timestamps.append(round(current_time, 2))
                else:
                    current_time += time_s
                    coordinates.append([end_node.x, end_node.y])
                    timestamps.append(round(current_time, 2))

            if len(coordinates) == len(timestamps) and len(coordinates) > 1:
                trips.append({
                    "type": agent_type,
                    "path": coordinates,
                    "timestamps": timestamps
                })

        except Exception as e:
            # Maybe no path found
            pass

    print(f"Generated {len(trips)} valid trips.")

    output = {
        "trips": trips
    }

    os.makedirs(os.path.join("data"), exist_ok=True)
    if not out_file:
        out_file = os.path.join("data", "trips.json")
    with open(out_file, "w") as f:
        json.dump(output, f)

    print(f"Saved trips to {out_file}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("num_trips_pos", nargs="?", type=int, default=None)
    parser.add_argument("--num_trips", type=int, default=150)
    parser.add_argument("--pattern", type=str, choices=["normal", "night", "weekend"], default="normal")
    parser.add_argument("--closed_streets", type=str, default="")
    parser.add_argument("--out", type=str, default="")

    args, unknown = parser.parse_known_args()

    # Try to parse legacy environment variable if no flags passed
    if args.num_trips_pos is not None:
        args.num_trips = args.num_trips_pos
    elif "NUM_TRIPS" in os.environ and args.num_trips == 150:
        try:
            args.num_trips = int(os.environ["NUM_TRIPS"])
        except ValueError:
            pass

    out_file = args.out if args.out else None

    generate_trips(num_trips=args.num_trips, pattern=args.pattern, closed_streets=args.closed_streets, out_file=out_file)
