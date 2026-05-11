import os
import json
import osmnx as ox

def get_almaty_roads_geojson():
    print("Fetching Almaty major roads...")
    custom_filter = '["highway"~"motorway|trunk|primary|secondary"]'
    G = ox.graph_from_place('Almaty, Kazakhstan', network_type='drive', custom_filter=custom_filter)

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
