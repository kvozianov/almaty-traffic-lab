import os
import json
import osmnx as ox
import networkx as nx

def get_almaty_roads_geojson():
    print("Fetching Almaty major roads...")

    # Add additional useful tags for simulation
    ox.settings.useful_tags_way += ['turn:lanes', 'turn:lanes:forward', 'turn:lanes:backward', 'maxspeed:forward', 'maxspeed:backward', 'restriction']

    custom_filter = '["highway"~"motorway|trunk|primary|secondary"]'
    G = ox.graph_from_place('Almaty, Kazakhstan', network_type='drive', custom_filter=custom_filter)

    # Convert to standard directed graph to handle parallel edges more easily, or keep as MultiDiGraph
    nodes, edges = ox.graph_to_gdfs(G)

    features = []
    for _, row in edges.iterrows():
        properties = {}
        for col in edges.columns:
            if col != 'geometry':
                val = row[col]
                if isinstance(val, list):
                    val = ', '.join(map(str, val))
                properties[col] = str(val) if not type(val) in (int, float, bool, str, type(None)) else val

        feature = {
            "type": "Feature",
            "geometry": row['geometry'].__geo_interface__,
            "properties": properties
        }
        features.append(feature)

    # Fetch turn restrictions which are relations in OSM
    # osmnx currently doesn't fetch relations easily in graph_from_place, but we can query them with overpass
    # For now, turn restrictions might be encoded in nodes or edges attributes if they were part of the way
    # If not, we still have lanes, maxspeed and basic routing

    geojson = {
        "type": "FeatureCollection",
        "features": features
    }

    os.makedirs('data', exist_ok=True)
    out_path = 'data/almaty_roads.geojson'

    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(geojson, f, ensure_ascii=False)

    print(f"Saved {len(features)} road segments to {out_path}.")

if __name__ == "__main__":
    get_almaty_roads_geojson()
