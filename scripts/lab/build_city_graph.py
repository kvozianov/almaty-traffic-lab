"""Build the compact Almaty road graph used by the in-browser traffic engine.

Input:  an Overpass JSON snapshot of Almaty drivable roads (committed in cache/).
Output: public/lab/city-graph.json (column-oriented, deterministic).

Pipeline: filter road classes -> split ways at intersections and signals ->
merge chains with identical attributes -> direct edges -> keep the largest
strongly connected component -> group edges into streets and selectable
sections. Standard library only.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from osm_names import english_name, short_name  # noqa: E402

SCHEMA = "almaty-traffic-lab/city-graph/v1"
DEFAULT_SNAPSHOT = Path("cache/910b537ad7f4f3eeb8738b353402448cfb888b2a.json")
DEFAULT_OUT = Path("public/lab/city-graph.json")

CLASSES = [
    "motorway", "trunk", "primary", "secondary", "tertiary",
    "motorway_link", "trunk_link", "primary_link", "secondary_link", "tertiary_link",
]
CLASS_RANK = {"motorway": 0, "trunk": 1, "primary": 2, "secondary": 3, "tertiary": 4}

# Vehicles per hour per lane at saturation (before signal green share).
CAP_PER_LANE = {
    "motorway": 1900, "trunk": 1800, "primary": 1700, "secondary": 1500, "tertiary": 1200,
}
LINK_CAP_PER_LANE = 1300
DEFAULT_LANES = {"motorway": 3, "trunk": 3, "primary": 2, "secondary": 2, "tertiary": 1}
DEFAULT_SPEED = {"motorway": 90, "trunk": 80, "primary": 60, "secondary": 60, "tertiary": 50}
LINK_SPEED = 40
URBAN_SPEED_FACTOR = 0.85  # free-flow speed is below the posted limit in a city

SIGNAL_GROUP_RADIUS_M = 45.0
SECTION_MIN_M = 600.0
SECTION_MAX_M = 1300.0
SIMPLIFY_TOLERANCE_M = 4.0
COORD_SCALE = 100_000  # 1e-5 degrees ~ 1 m


# ---------------------------------------------------------------- geometry

def haversine_m(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    r = 6_371_008.8
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


LAT0 = 43.24
M_PER_DEG_LAT = 111_132.0
M_PER_DEG_LON = 111_320.0 * math.cos(math.radians(LAT0))


def to_xy(lon: float, lat: float) -> tuple[float, float]:
    return lon * M_PER_DEG_LON, lat * M_PER_DEG_LAT


def simplify(points: list[tuple[float, float]], tol_m: float) -> list[tuple[float, float]]:
    """Iterative Douglas-Peucker on lon/lat using a local metric projection."""
    if len(points) <= 2:
        return points
    xy = [to_xy(*p) for p in points]
    keep = [False] * len(points)
    keep[0] = keep[-1] = True
    stack = [(0, len(points) - 1)]
    while stack:
        i, j = stack.pop()
        ax, ay = xy[i]
        bx, by = xy[j]
        dx, dy = bx - ax, by - ay
        norm = math.hypot(dx, dy)
        best, best_k = -1.0, -1
        for k in range(i + 1, j):
            px, py = xy[k]
            if norm == 0:
                d = math.hypot(px - ax, py - ay)
            else:
                d = abs(dy * px - dx * py + bx * ay - by * ax) / norm
            if d > best:
                best, best_k = d, k
        if best > tol_m:
            keep[best_k] = True
            stack.append((i, best_k))
            stack.append((best_k, j))
    return [p for p, k in zip(points, keep) if k]


# ---------------------------------------------------------------- tags

def base_class(highway: str) -> str:
    return highway[:-5] if highway.endswith("_link") else highway


def parse_int(value: str | None) -> int | None:
    if not value:
        return None
    m = re.match(r"\s*(\d+)", value.split(";")[0])
    return int(m.group(1)) if m else None


def parse_speed(value: str | None) -> float | None:
    if not value:
        return None
    if value.strip().upper() == "RU:URBAN":
        return 60.0
    m = re.match(r"\s*(\d+(?:\.\d+)?)", value)
    if not m:
        return None
    speed = float(m.group(1))
    if "mph" in value:
        speed *= 1.609
    return speed if 5 <= speed <= 130 else None


def way_attributes(tags: dict[str, str]) -> dict | None:
    highway = tags.get("highway", "")
    if highway not in CLASSES:
        return None
    if tags.get("area") == "yes" or tags.get("access") in {"no", "private"}:
        return None
    if tags.get("motor_vehicle") == "no" or tags.get("motorcar") == "no":
        return None
    cls = base_class(highway)
    is_link = highway.endswith("_link")

    oneway_tag = tags.get("oneway", "").lower()
    if oneway_tag in {"yes", "true", "1"} or tags.get("junction") in {"roundabout", "circular"}:
        direction = 1
    elif oneway_tag == "-1":
        direction = -1
    elif is_link and oneway_tag != "no":
        direction = 1  # OSM convention: links are one-way unless tagged otherwise
    else:
        direction = 0

    lanes_total = parse_int(tags.get("lanes"))
    lanes_f = parse_int(tags.get("lanes:forward"))
    lanes_b = parse_int(tags.get("lanes:backward"))
    default = 1 if is_link else DEFAULT_LANES[cls]
    if direction != 0:
        lf = lanes_total or default
        lb = 0
    else:
        half = math.ceil(lanes_total / 2) if lanes_total else default
        lf = lanes_f or half
        lb = lanes_b or half
    # For oneway=-1 the node order is reversed in split_segments, so the
    # single travel direction is always "forward" here.
    lf = max(0, min(lf, 6))
    lb = max(0, min(lb, 6))

    speed = parse_speed(tags.get("maxspeed")) or (LINK_SPEED if is_link else DEFAULT_SPEED[cls])
    return {
        "highway": highway,
        "cls": cls,
        "link": is_link,
        "lanesF": lf,
        "lanesB": lb,
        "reverse": direction == -1,
        "speed": round(speed * URBAN_SPEED_FACTOR, 1),
        "cap": LINK_CAP_PER_LANE if is_link else CAP_PER_LANE[cls],
        "name": street_key(tags),
        "nameEn": english_name(tags),
        "hasEn": bool(tags.get("name:en")),
        "nameLocal": tags.get("name"),
    }


def street_key(tags: dict[str, str]) -> str | None:
    """Group key for one street: the Russian name is the most consistent tag."""
    raw = tags.get("name:ru") or tags.get("name")
    return re.sub(r"\s+", " ", raw.strip().lower()) if raw else None


# ---------------------------------------------------------------- build

def load_snapshot(path: Path):
    payload = json.loads(path.read_text(encoding="utf-8"))
    nodes, signals, ways = {}, set(), []
    for el in payload["elements"]:
        if el["type"] == "node":
            nodes[el["id"]] = (el["lon"], el["lat"])
            if el.get("tags", {}).get("highway") == "traffic_signals":
                signals.add(el["id"])
        elif el["type"] == "way":
            ways.append(el)
    ways.sort(key=lambda w: w["id"])
    return payload.get("osm3s", {}), nodes, signals, ways


def split_segments(nodes, signals, ways):
    """Split filtered ways into segments between intersections/signals."""
    kept = []
    for way in ways:
        attrs = way_attributes(way.get("tags", {}))
        if attrs is None:
            continue
        refs = [n for n in way["nodes"] if n in nodes]
        if attrs["reverse"]:
            refs = refs[::-1]
        if len(refs) >= 2:
            kept.append((way["id"], refs, attrs))

    use = defaultdict(int)
    for _, refs, _ in kept:
        for n in refs:
            use[n] += 1
        use[refs[0]] += 1
        use[refs[-1]] += 1

    segments = []
    for way_id, refs, attrs in kept:
        start = 0
        for i in range(1, len(refs)):
            n = refs[i]
            if i == len(refs) - 1 or use[n] >= 2 or n in signals:
                seg_nodes = refs[start:i + 1]
                if len(seg_nodes) >= 2 and seg_nodes[0] != seg_nodes[-1]:
                    segments.append({"nodes": seg_nodes, "attrs": attrs, "way": way_id})
                start = i
    return segments


def attr_key(attrs: dict) -> tuple:
    return (attrs["highway"], attrs["name"], attrs["speed"], attrs["cap"])


def reversed_segment(seg: dict) -> dict:
    a = dict(seg["attrs"])
    a["lanesF"], a["lanesB"] = a["lanesB"], a["lanesF"]
    return {"nodes": seg["nodes"][::-1], "attrs": a, "way": seg["way"]}


def merge_chains(segments, signals):
    """Merge consecutive segments joined at a plain degree-2 node."""
    alive = {i: s for i, s in enumerate(segments)}
    at_node = defaultdict(set)
    for i, s in alive.items():
        at_node[s["nodes"][0]].add(i)
        at_node[s["nodes"][-1]].add(i)

    changed = True
    while changed:
        changed = False
        for n in sorted(at_node):
            ids = at_node[n]
            if n in signals or len(ids) != 2:
                continue
            i, j = sorted(ids)
            a, b = alive[i], alive[j]
            if a["nodes"][-1] != n:
                a = reversed_segment(a)
            if b["nodes"][0] != n:
                b = reversed_segment(b)
            if a["nodes"][-1] != n or b["nodes"][0] != n:
                continue
            if a["nodes"][0] == b["nodes"][-1]:
                continue  # would create a loop
            if attr_key(a["attrs"]) != attr_key(b["attrs"]):
                continue
            if (a["attrs"]["lanesF"], a["attrs"]["lanesB"]) != (b["attrs"]["lanesF"], b["attrs"]["lanesB"]):
                continue
            merged = {"nodes": a["nodes"] + b["nodes"][1:], "attrs": a["attrs"], "way": min(a["way"], b["way"])}
            del alive[j]
            alive[i] = merged
            at_node[n].clear()
            other_end = merged["nodes"][-1]
            at_node[other_end].discard(j)
            at_node[other_end].add(i)
            start = merged["nodes"][0]
            at_node[start].add(i)
            changed = True
    return [alive[k] for k in sorted(alive)]


def largest_scc(num_nodes: int, edges: list[tuple[int, int]]) -> set[int]:
    """Iterative Kosaraju."""
    out_adj = [[] for _ in range(num_nodes)]
    in_adj = [[] for _ in range(num_nodes)]
    for u, v in edges:
        out_adj[u].append(v)
        in_adj[v].append(u)
    visited = [False] * num_nodes
    order = []
    for s in range(num_nodes):
        if visited[s]:
            continue
        visited[s] = True
        stack = [(s, 0)]
        while stack:
            node, idx = stack[-1]
            if idx < len(out_adj[node]):
                stack[-1] = (node, idx + 1)
                nxt = out_adj[node][idx]
                if not visited[nxt]:
                    visited[nxt] = True
                    stack.append((nxt, 0))
            else:
                stack.pop()
                order.append(node)
    comp = [-1] * num_nodes
    sizes = []
    for s in reversed(order):
        if comp[s] != -1:
            continue
        cid = len(sizes)
        comp[s] = cid
        size = 0
        stack = [s]
        while stack:
            node = stack.pop()
            size += 1
            for nxt in in_adj[node]:
                if comp[nxt] == -1:
                    comp[nxt] = cid
                    stack.append(nxt)
        sizes.append(size)
    best = max(range(len(sizes)), key=lambda c: sizes[c])
    return {i for i in range(num_nodes) if comp[i] == best}


def group_signals(signal_nodes: list[int], lon: list[float], lat: list[float]) -> dict[int, int]:
    """Cluster signal nodes of one junction (dual carriageways have several)."""
    parent = {n: n for n in signal_nodes}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    cell = 0.001
    buckets = defaultdict(list)
    for n in signal_nodes:
        buckets[(int(lon[n] / cell), int(lat[n] / cell))].append(n)
    for n in signal_nodes:
        cx, cy = int(lon[n] / cell), int(lat[n] / cell)
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for m in buckets.get((cx + dx, cy + dy), []):
                    if m > n and haversine_m(lon[n], lat[n], lon[m], lat[m]) <= SIGNAL_GROUP_RADIUS_M:
                        parent[find(m)] = find(n)
    roots = sorted({find(n) for n in signal_nodes})
    gid = {r: i for i, r in enumerate(roots)}
    return {n: gid[find(n)] for n in signal_nodes}


def build_sections(streets, seg_street, seg_nodes_idx, seg_len, node_streets, lon, lat, street_rank):
    """Cut each street into ~0.6-1.5 km sections along its main axis."""
    sections = []
    seg_section = [-1] * len(seg_street)
    by_street = defaultdict(list)
    for s, st in enumerate(seg_street):
        if st >= 0:
            by_street[st].append(s)

    for st in sorted(by_street):
        segs = by_street[st]
        pts = [to_xy(lon[n], lat[n]) for s in segs for n in seg_nodes_idx[s]]
        mx = sum(p[0] for p in pts) / len(pts)
        my = sum(p[1] for p in pts) / len(pts)
        sxx = sum((p[0] - mx) ** 2 for p in pts)
        syy = sum((p[1] - my) ** 2 for p in pts)
        sxy = sum((p[0] - mx) * (p[1] - my) for p in pts)
        angle = 0.5 * math.atan2(2 * sxy, sxx - syy)
        ux, uy = math.cos(angle), math.sin(angle)

        def proj(n):
            x, y = to_xy(lon[n], lat[n])
            return (x - mx) * ux + (y - my) * uy

        # Orient west->east / south->north for stable labels.
        all_nodes = {n for s in segs for n in seg_nodes_idx[s]}
        lo = min(all_nodes, key=proj)
        hi = max(all_nodes, key=proj)
        if (lon[hi] - lon[lo]) + (lat[hi] - lat[lo]) < 0:
            ux, uy = -ux, -uy
        p_min = min(proj(n) for n in all_nodes)
        p_max = max(proj(n) for n in all_nodes)

        # Candidate cut points: junctions with another named significant street.
        candidates = []
        for n in all_nodes:
            others = [o for o in node_streets.get(n, ()) if o != st and street_rank[o] <= CLASS_RANK["tertiary"]]
            if others:
                best = min(others, key=lambda o: (street_rank[o], streets[o]["name"]))
                candidates.append((proj(n), street_rank[best], best))
        candidates.sort()

        cuts = [(p_min, None)]
        last = p_min
        i = 0
        while i < len(candidates):
            pos, _, other = candidates[i]
            if pos - last >= SECTION_MIN_M and p_max - pos >= SECTION_MIN_M * 0.5:
                # Among candidates up to the max window, prefer the most significant cross street.
                window = [c for c in candidates[i:] if c[0] - last <= SECTION_MAX_M]
                pick = min(window, key=lambda c: (c[1], -c[0])) if window else candidates[i]
                cuts.append((pick[0], pick[2]))
                last = pick[0]
                i = candidates.index(pick) + 1
                continue
            i += 1
        cuts.append((p_max + 1e-6, None))

        first_section = len(sections)
        for k in range(len(cuts) - 1):
            sections.append({
                "street": st,
                "from": cuts[k][1],
                "to": cuts[k + 1][1],
                "span": cuts[k + 1][0] - cuts[k][0],
                "segs": [],
            })
        for s in segs:
            nodes_s = seg_nodes_idx[s]
            mid = 0.5 * (proj(nodes_s[0]) + proj(nodes_s[-1]))
            k = 0
            while k + 1 < len(cuts) - 1 and mid >= cuts[k + 1][0]:
                k += 1
            seg_section[s] = first_section + k
            sections[first_section + k]["segs"].append(s)

    # Drop empty sections and re-index.
    remap, kept = {}, []
    for i, sec in enumerate(sections):
        if sec["segs"]:
            remap[i] = len(kept)
            kept.append(sec)
    seg_section = [remap.get(x, -1) if x >= 0 else -1 for x in seg_section]
    for sec in kept:
        # Axis span, so dual carriageways are not counted twice.
        sec["lengthM"] = round(min(sec["span"], sum(seg_len[s] for s in sec["segs"])), 1)
    return kept, seg_section


def build(snapshot: Path) -> dict:
    meta, nodes, signals, ways = load_snapshot(snapshot)
    segments = split_segments(nodes, signals, ways)
    raw_segment_count = len(segments)
    segments = merge_chains(segments, signals)

    # Directed edges over OSM node ids.
    osm_ids = sorted({n for s in segments for n in (s["nodes"][0], s["nodes"][-1])})
    index = {n: i for i, n in enumerate(osm_ids)}
    directed = []
    for si, s in enumerate(segments):
        a, b = index[s["nodes"][0]], index[s["nodes"][-1]]
        if s["attrs"]["lanesF"] > 0:
            directed.append((a, b))
        if s["attrs"]["lanesB"] > 0:
            directed.append((b, a))
    keep_nodes = largest_scc(len(osm_ids), directed)

    # Keep segments whose both ends are in the component.
    segments = [s for s in segments if index[s["nodes"][0]] in keep_nodes and index[s["nodes"][-1]] in keep_nodes]
    end_ids = sorted({n for s in segments for n in (s["nodes"][0], s["nodes"][-1])})
    nidx = {n: i for i, n in enumerate(end_ids)}
    lon = [round(nodes[n][0], 6) for n in end_ids]
    lat = [round(nodes[n][1], 6) for n in end_ids]
    node_signal = [1 if n in signals else 0 for n in end_ids]

    # Streets
    street_names = sorted({s["attrs"]["name"] for s in segments if s["attrs"]["name"] and not s["attrs"]["link"]})
    street_index = {name: i for i, name in enumerate(street_names)}
    local_names: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    en_names: dict[str, dict[tuple, int]] = defaultdict(lambda: defaultdict(int))
    street_rank = [9] * len(street_names)
    for s in segments:
        name = s["attrs"]["name"]
        if name in street_index and not s["attrs"]["link"]:
            st = street_index[name]
            street_rank[st] = min(street_rank[st], CLASS_RANK[s["attrs"]["cls"]])
            if s["attrs"]["nameLocal"]:
                local_names[name][s["attrs"]["nameLocal"]] += 1
            if s["attrs"]["nameEn"]:
                # Prefer real name:en tags over transliterations.
                en_names[name][(s["attrs"]["hasEn"], s["attrs"]["nameEn"])] += 1

    def most_common(counter):
        return max(sorted(counter), key=lambda k: counter[k]) if counter else None

    streets = []
    for name in street_names:
        en = en_names.get(name)
        best_en = max(sorted(en), key=lambda k: (k[0], en[k])) if en else None
        streets.append({"name": best_en[1] if best_en else name, "nameLocal": most_common(local_names.get(name))})

    seg_street, seg_nodes_idx, seg_len, seg_geom = [], [], [], []
    node_streets: dict[int, set[int]] = defaultdict(set)
    for s in segments:
        name = s["attrs"]["name"]
        st = street_index[name] if (name in street_index and not s["attrs"]["link"]) else -1
        seg_street.append(st)
        pts = [nodes[n] for n in s["nodes"]]
        length = sum(haversine_m(*pts[k], *pts[k + 1]) for k in range(len(pts) - 1))
        seg_len.append(length)
        seg_geom.append(simplify(pts, SIMPLIFY_TOLERANCE_M))
        a, b = nidx[s["nodes"][0]], nidx[s["nodes"][-1]]
        seg_nodes_idx.append([a, b])
        if st >= 0:
            node_streets[a].add(st)
            node_streets[b].add(st)

    sections, seg_section = build_sections(streets, seg_street, seg_nodes_idx, seg_len, node_streets, lon, lat, street_rank)

    signal_group_map = group_signals([i for i, v in enumerate(node_signal) if v], lon, lat)
    signal_group = [signal_group_map.get(i, -1) for i in range(len(end_ids))]

    classes = CLASSES
    cls_index = {c: i for i, c in enumerate(classes)}

    # Geometry table (one entry per segment, shared by both directions).
    geom_flat, geom_offset = [], [0]
    for pts in seg_geom:
        for x, y in pts:
            geom_flat.append(round(x * COORD_SCALE))
            geom_flat.append(round(y * COORD_SCALE))
        geom_offset.append(len(geom_flat) // 2)

    edges = {k: [] for k in ("from", "to", "length", "freeSpeed", "lanes", "capPerLane", "cls", "street", "section", "seg", "rev")}
    for si, s in enumerate(segments):
        a, b = seg_nodes_idx[si]
        at = s["attrs"]
        for frm, to, lanes, rev in ((a, b, at["lanesF"], 0), (b, a, at["lanesB"], 1)):
            if lanes <= 0:
                continue
            edges["from"].append(frm)
            edges["to"].append(to)
            edges["length"].append(round(seg_len[si], 1))
            edges["freeSpeed"].append(at["speed"])
            edges["lanes"].append(lanes)
            edges["capPerLane"].append(at["cap"])
            edges["cls"].append(cls_index[at["highway"]])
            edges["street"].append(seg_street[si])
            edges["section"].append(seg_section[si])
            edges["seg"].append(si)
            edges["rev"].append(rev)

    # Section metadata
    section_out = []
    edge_by_seg = defaultdict(list)
    for e, si in enumerate(edges["seg"]):
        edge_by_seg[si].append(e)
    for sec in sections:
        name = streets[sec["street"]]["name"]
        frm = short_name(streets[sec["from"]]["name"]) if sec["from"] is not None else None
        to = short_name(streets[sec["to"]]["name"]) if sec["to"] is not None else None
        if frm and to:
            label = f"{frm} → {to}"
        elif to:
            label = f"up to {to}"
        elif frm:
            label = f"from {frm}"
        else:
            label = "whole street"
        sec_edges = sorted(e for si in sec["segs"] for e in edge_by_seg[si])
        xs = [lon[edges["from"][e]] for e in sec_edges] + [lon[edges["to"][e]] for e in sec_edges]
        ys = [lat[edges["from"][e]] for e in sec_edges] + [lat[edges["to"][e]] for e in sec_edges]
        min_lanes = min(edges["lanes"][e] for e in sec_edges)
        section_out.append({
            "street": sec["street"],
            "label": label,
            "lengthM": sec["lengthM"],
            "edges": sec_edges,
            "minLanes": min_lanes,
            "signals": sum(1 for e in sec_edges if node_signal[edges["to"][e]]),
            "bbox": [round(min(xs), 5), round(min(ys), 5), round(max(xs), 5), round(max(ys), 5)],
        })

    return {
        "schema": SCHEMA,
        "source": {
            "snapshot": snapshot.as_posix(),
            "osmTimestamp": meta.get("timestamp_osm_base"),
            "license": "ODbL-1.0",
            "attribution": "© OpenStreetMap contributors",
        },
        "params": {
            "classes": CLASSES,
            "capPerLane": CAP_PER_LANE,
            "linkCapPerLane": LINK_CAP_PER_LANE,
            "urbanSpeedFactor": URBAN_SPEED_FACTOR,
            "coordScale": COORD_SCALE,
        },
        "stats": {
            "rawSegments": raw_segment_count,
            "segments": len(segments),
            "nodes": len(end_ids),
            "edges": len(edges["from"]),
            "signals": sum(node_signal),
            "signalGroups": len(set(signal_group_map.values())),
            "streets": len(streets),
            "sections": len(section_out),
        },
        "nodes": {"lon": lon, "lat": lat, "signal": node_signal, "signalGroup": signal_group},
        "edges": edges,
        "geometry": {"offset": geom_offset, "coords": geom_flat},
        "classes": classes,
        "streets": streets,
        "sections": section_out,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, default=DEFAULT_SNAPSHOT)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    graph = build(args.snapshot)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(graph, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(json.dumps(graph["stats"], indent=2))
    print(f"wrote {args.out} ({args.out.stat().st_size / 1e6:.2f} MB)")


if __name__ == "__main__":
    main()
