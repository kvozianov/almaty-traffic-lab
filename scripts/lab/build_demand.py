"""Build the zone system and morning-peak trip matrix for the traffic lab.

All values are *proxy* estimates; Almaty has no public origin-destination
survey. The method is transparent and documented in /methods:

* Zones: a 2 km grid over the road graph; cells without graph nodes are dropped.
* Productions (homes): length of residential streets in the cell (OSM).
* Attractions (jobs, services): length of all streets in the cell, boosted
  towards the central business district.
* Distribution: production-constrained gravity model on free-flow travel time.

Output public/lab/demand.json holds a normalised matrix (sum = 1). The engine
multiplies it by ``totalTrips`` from data/lab/calibration.json.
"""

from __future__ import annotations

import argparse
import heapq
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_city_graph import DEFAULT_SNAPSHOT, haversine_m, load_snapshot  # noqa: E402

SCHEMA = "almaty-traffic-lab/demand/v1"
GRAPH = Path("public/lab/city-graph.json")
DEFAULT_OUT = Path("public/lab/demand.json")

CELL_M = 2000.0
LAT0 = 43.24
M_PER_DEG_LAT = 111_132.0
M_PER_DEG_LON = 111_320.0 * math.cos(math.radians(LAT0))

CBD = (76.945, 43.245)  # Almaty "golden square": Abay / Dostyk / Al-Farabi
CBD_BOOST = 3.0
CBD_RADIUS_M = 3500.0
BETA_PER_MIN = 0.10
CONNECTORS = 3
ACCESS_SPEED_KMH = 20.0
MIN_ZONE_WEIGHT_SHARE = 0.002

HOME_CLASSES = {"residential", "living_street"}
STREET_CLASSES = HOME_CLASSES | {
    "unclassified", "tertiary", "tertiary_link", "secondary", "secondary_link",
    "primary", "primary_link", "trunk", "trunk_link",
}


def cell_of(lon: float, lat: float, origin: tuple[float, float]) -> tuple[int, int]:
    return (
        int((lon - origin[0]) * M_PER_DEG_LON // CELL_M),
        int((lat - origin[1]) * M_PER_DEG_LAT // CELL_M),
    )


def street_lengths(snapshot: Path, origin):
    _, nodes, _, ways = load_snapshot(snapshot)
    homes = defaultdict(float)
    streets = defaultdict(float)
    for way in ways:
        highway = way.get("tags", {}).get("highway")
        if highway not in STREET_CLASSES:
            continue
        refs = [n for n in way["nodes"] if n in nodes]
        for a, b in zip(refs, refs[1:]):
            (x1, y1), (x2, y2) = nodes[a], nodes[b]
            length = haversine_m(x1, y1, x2, y2)
            cell = cell_of((x1 + x2) / 2, (y1 + y2) / 2, origin)
            streets[cell] += length
            if highway in HOME_CLASSES:
                homes[cell] += length
    return homes, streets


def free_flow_graph(graph: dict):
    e = graph["edges"]
    n = len(graph["nodes"]["lon"])
    adj = [[] for _ in range(n)]
    signal = graph["nodes"]["signal"]
    for i in range(len(e["from"])):
        minutes = e["length"][i] / (e["freeSpeed"][i] / 3.6) / 60.0
        if signal[e["to"][i]]:
            minutes += 0.19  # uniform Webster delay at 50 % green, 90 s cycle (11.25 s)
        adj[e["from"][i]].append((e["to"][i], minutes))
    return adj


def multi_source_dijkstra(adj, sources: list[tuple[int, float]]):
    dist = [math.inf] * len(adj)
    heap = []
    for node, d in sources:
        if d < dist[node]:
            dist[node] = d
            heapq.heappush(heap, (d, node))
    while heap:
        d, u = heapq.heappop(heap)
        if d > dist[u]:
            continue
        for v, w in adj[u]:
            nd = d + w
            if nd < dist[v]:
                dist[v] = nd
                heapq.heappush(heap, (nd, v))
    return dist


def build(graph_path: Path, snapshot: Path) -> dict:
    graph = json.loads(graph_path.read_text(encoding="utf-8"))
    lon, lat = graph["nodes"]["lon"], graph["nodes"]["lat"]
    origin = (min(lon), min(lat))

    nodes_in_cell = defaultdict(list)
    for i, (x, y) in enumerate(zip(lon, lat)):
        nodes_in_cell[cell_of(x, y, origin)].append(i)

    homes, streets = street_lengths(snapshot, origin)

    # Candidate zones = cells with graph nodes.
    raw = []
    for cell in sorted(nodes_in_cell):
        cx = origin[0] + (cell[0] + 0.5) * CELL_M / M_PER_DEG_LON
        cy = origin[1] + (cell[1] + 0.5) * CELL_M / M_PER_DEG_LAT
        d_cbd = haversine_m(cx, cy, *CBD)
        boost = 1.0 + CBD_BOOST * math.exp(-((d_cbd / CBD_RADIUS_M) ** 2))
        raw.append({
            "cell": cell,
            "center": (cx, cy),
            "production": homes.get(cell, 0.0),
            "attraction": streets.get(cell, 0.0) * boost,
        })
    total_p = sum(z["production"] for z in raw)
    total_a = sum(z["attraction"] for z in raw)
    zones = [
        z for z in raw
        if z["production"] / total_p >= MIN_ZONE_WEIGHT_SHARE or z["attraction"] / total_a >= MIN_ZONE_WEIGHT_SHARE
    ]

    # Connectors: nearest graph nodes to the zone's centre, within the cell.
    adj = free_flow_graph(graph)
    out_degree = [len(a) for a in adj]
    for z in zones:
        cands = [i for i in nodes_in_cell[z["cell"]] if out_degree[i] > 0]
        cands.sort(key=lambda i: (haversine_m(lon[i], lat[i], *z["center"]), i))
        picked = cands[:CONNECTORS]
        z["connectors"] = [
            [i, round(haversine_m(lon[i], lat[i], *z["center"]) / (ACCESS_SPEED_KMH / 3.6) / 60.0, 3)]
            for i in picked
        ]

    # Free-flow zone-to-zone times.
    times = []
    for zo in zones:
        dist = multi_source_dijkstra(adj, [(n, t) for n, t in zo["connectors"]])
        row = []
        for zd in zones:
            row.append(min(dist[n] + t for n, t in zd["connectors"]))
        times.append(row)

    # Production-constrained gravity model.
    trips = []
    for i, zo in enumerate(zones):
        weights = []
        for j, zd in enumerate(zones):
            if i == j or not math.isfinite(times[i][j]):
                weights.append(0.0)
            else:
                weights.append(zd["attraction"] * math.exp(-BETA_PER_MIN * times[i][j]))
        s = sum(weights)
        if s == 0 or zo["production"] == 0:
            continue
        for j, w in enumerate(weights):
            if w > 0:
                trips.append((i, j, zo["production"] * w / s))
    total = sum(t for _, _, t in trips)
    matrix = [[i, j, round(t / total, 9)] for i, j, t in trips if t / total >= 1e-7]

    return {
        "schema": SCHEMA,
        "claimLevel": "proxy",
        "method": {
            "cellM": CELL_M,
            "production": "residential + living_street length (OSM)",
            "attraction": f"all street length x (1 + {CBD_BOOST} * exp(-(d_cbd/{CBD_RADIUS_M:.0f} m)^2))",
            "distribution": f"production-constrained gravity, exp(-{BETA_PER_MIN} * free-flow minutes)",
            "connectors": f"{CONNECTORS} nearest graph nodes, access at {ACCESS_SPEED_KMH:.0f} km/h",
            "cbd": CBD,
        },
        "periods": {
            "am": {"label": "Morning peak", "factor": 1.0, "transpose": False},
            "midday": {"label": "Midday", "factor": 0.6, "transpose": "mix"},
            "pm": {"label": "Evening peak", "factor": 0.95, "transpose": True},
            "night": {"label": "Night", "factor": 0.15, "transpose": "mix"},
        },
        "zones": [
            {
                "center": [round(z["center"][0], 5), round(z["center"][1], 5)],
                "production": round(z["production"] / total_p, 6),
                "attraction": round(z["attraction"] / total_a, 6),
                "connectors": z["connectors"],
            }
            for z in zones
        ],
        "matrix": matrix,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--graph", type=Path, default=GRAPH)
    parser.add_argument("--snapshot", type=Path, default=DEFAULT_SNAPSHOT)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    demand = build(args.graph, args.snapshot)
    args.out.write_text(json.dumps(demand, separators=(",", ":")), encoding="utf-8")
    print(f"zones={len(demand['zones'])} od_pairs={len(demand['matrix'])}")
    print(f"wrote {args.out} ({args.out.stat().st_size / 1e3:.0f} kB)")


if __name__ == "__main__":
    main()
