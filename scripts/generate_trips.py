import sys
import os
import random
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from traffic_sim.graph_cache import load_preset_graph

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
            timestamps.append(int(current_time))

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
                current_time += time_s

                coordinates.append([end_node.x, end_node.y])
                timestamps.append(int(current_time))

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
    generate_trips()
