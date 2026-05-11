import json
import random
import os

def generate_traffic():
    input_file = os.path.join("data", "almaty_roads.geojson")
    output_file = os.path.join("data", "traffic_data.json")

    try:
        with open(input_file, "r", encoding="utf-8") as f:
            content = f.read()
            # Fix NaN serialization from OSMnx
            content = content.replace('NaN', 'null')
            geojson = json.loads(content)
    except FileNotFoundError:
        print(f"Error: {input_file} not found.")
        return

    roads = []
    lights = []
    light_locations = set()

    for feature in geojson.get("features", []):
        props = feature.get("properties", {})
        # Ensure id is a string
        road_id = str(props.get("osmid", ""))

        # Density between 0 and 1
        density = round(random.uniform(0.0, 1.0), 2)

        roads.append({
            "id": road_id,
            "density": density
        })

        geometry = feature.get("geometry", {})
        if geometry.get("type") == "LineString":
            coords = geometry.get("coordinates", [])
            if len(coords) > 0:
                # Add start and end points as potential traffic light locations
                # Using round to group nearby points
                light_locations.add((coords[0][0], coords[0][1]))
                light_locations.add((coords[-1][0], coords[-1][1]))

    # Sample some lights
    sampled_locations = random.sample(list(light_locations), min(50, len(light_locations)))
    for loc in sampled_locations:
        lights.append({
            "coordinates": [loc[0], loc[1]],
            "color": random.choice(["red", "yellow", "green"])
        })

    result = {
        "lights": lights,
        "roads": roads
    }

    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    print(f"Traffic data generated successfully at {output_file}")

if __name__ == "__main__":
    generate_traffic()
