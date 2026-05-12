import os
import json
import random

def generate_physics():
    input_file = os.path.join("data", "almaty_roads.geojson")
    output_file = os.path.join("data", "physics.json")

    try:
        with open(input_file, "r", encoding="utf-8") as f:
            content = f.read()
            content = content.replace('NaN', 'null')
            geojson = json.loads(content)
    except FileNotFoundError:
        print(f"Error: {input_file} not found.")
        return

    uncontrolled_intersections = []
    pedestrian_crossings = []

    nodes_seen = set()
    features = geojson.get("features", [])

    for feature in features:
        geometry = feature.get("geometry", {})
        if geometry.get("type") == "LineString":
            coords = geometry.get("coordinates", [])
            if len(coords) > 0:
                # Potential intersections at the start and end of road segments
                nodes_seen.add((coords[0][0], coords[0][1]))
                nodes_seen.add((coords[-1][0], coords[-1][1]))

                # Mid-block pedestrian crossings
                if len(coords) > 2 and random.random() < 0.1: # 10% chance for a mid-segment crossing
                    mid_idx = len(coords) // 2
                    pedestrian_crossings.append({
                        "coordinates": [coords[mid_idx][0], coords[mid_idx][1]],
                        "type": "pedestrian_crossing"
                    })

    # Pick some nodes as uncontrolled intersections (excluding signalized ones implicitly for now)
    node_list = list(nodes_seen)
    sampled_intersections = random.sample(node_list, min(100, len(node_list)))

    for loc in sampled_intersections:
        uncontrolled_intersections.append({
            "coordinates": [loc[0], loc[1]],
            "type": "uncontrolled_intersection"
        })

    result = {
        "uncontrolled_intersections": uncontrolled_intersections,
        "pedestrian_crossings": pedestrian_crossings
    }

    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    print(f"Physics data generated successfully at {output_file}")

if __name__ == "__main__":
    generate_physics()
