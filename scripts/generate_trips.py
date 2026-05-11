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

def generate_trips(num_trips=150):
    print("Loading graph...")
    graph = load_preset_graph("full_almaty_fast")
    nodes_list = list(graph.nodes.keys())

    trips = []

    print(f"Generating {num_trips} trips...")
    for i in range(num_trips):
        start = random.choice(nodes_list)
        end = random.choice(nodes_list)

        # Ensure start and end are different
        while start == end:
            end = random.choice(nodes_list)

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
    out_file = os.path.join("data", "trips.json")
    with open(out_file, "w") as f:
        json.dump(output, f)

    print(f"Saved trips to {out_file}")

if __name__ == "__main__":
    try:
        trip_count = int(sys.argv[1]) if len(sys.argv) > 1 else 150
    except ValueError:
        trip_count = 150

    generate_trips(trip_count)
