from __future__ import annotations

import html
import json
from dataclasses import asdict, dataclass
from math import hypot
from pathlib import Path

from .network import CityGraph
from .simulation import TrafficSimulation


@dataclass(slots=True)
class VehicleFrame:
    vehicle_id: str
    x: float
    y: float
    state: str


@dataclass(slots=True)
class SimulationFrame:
    tick: int
    sim_time_s: float
    vehicles: list[VehicleFrame]


def record_frames(sim: TrafficSimulation, steps: int) -> list[SimulationFrame]:
    frames = [_build_frame(sim)]
    for _ in range(steps):
        sim.step()
        frames.append(_build_frame(sim))
    return frames


def write_visualization_html(
    output_path: str | Path,
    graph: CityGraph,
    sim: TrafficSimulation,
    frames: list[SimulationFrame],
    title: str = "Traffic Simulation",
) -> Path:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = _build_payload(graph, sim, frames)
    output.write_text(_render_html(title, payload), encoding="utf-8")
    return output


def _build_frame(sim: TrafficSimulation) -> SimulationFrame:
    vehicles: list[VehicleFrame] = []
    for vehicle in sim.vehicles.values():
        if vehicle.state != "moving" or vehicle.current_road_id is None:
            continue
        x, y = _vehicle_position(sim.graph, vehicle.current_road_id, vehicle.progress_m)
        vehicles.append(VehicleFrame(vehicle.vehicle_id, x, y, vehicle.state))
    return SimulationFrame(tick=sim.tick, sim_time_s=sim.sim_time_s, vehicles=vehicles)


def _vehicle_position(graph: CityGraph, road_id: str, progress_m: float) -> tuple[float, float]:
    road = graph.roads[road_id]
    points = graph.road_geometry(road_id)
    ratio = min(1.0, max(0.0, progress_m / max(road.length_m, 1.0)))
    return _interpolate_polyline(points, ratio)


def _interpolate_polyline(points: list[tuple[float, float]], ratio: float) -> tuple[float, float]:
    if len(points) == 1:
        return points[0]

    segment_lengths: list[float] = []
    total_length = 0.0
    for start, end in zip(points, points[1:]):
        length = hypot(end[0] - start[0], end[1] - start[1])
        segment_lengths.append(length)
        total_length += length

    if total_length == 0:
        return points[0]

    target = total_length * ratio
    walked = 0.0
    for index, length in enumerate(segment_lengths):
        if walked + length >= target:
            local_ratio = (target - walked) / length if length else 0.0
            start = points[index]
            end = points[index + 1]
            return (
                start[0] + (end[0] - start[0]) * local_ratio,
                start[1] + (end[1] - start[1]) * local_ratio,
            )
        walked += length
    return points[-1]


def _build_payload(graph: CityGraph, sim: TrafficSimulation, frames: list[SimulationFrame]) -> dict[str, object]:
    raw_roads = [
        {
            "id": road_id,
            "points": graph.road_geometry(road_id),
            "load": sim.peak_road_loads().get(road_id, 0.0),
            "isOpen": graph.roads[road_id].is_open,
        }
        for road_id in graph.roads
    ]
    bounds = _bounds([point for road in raw_roads for point in road["points"]])
    roads = [
        {
            "id": road["id"],
            "points": [_project_point(point, bounds) for point in road["points"]],
            "load": road["load"],
            "isOpen": road["isOpen"],
        }
        for road in raw_roads
    ]
    projected_frames = [
        {
            "tick": frame.tick,
            "simTimeS": frame.sim_time_s,
            "vehicles": [
                {
                    "id": vehicle.vehicle_id,
                    "x": _project_point((vehicle.x, vehicle.y), bounds)[0],
                    "y": _project_point((vehicle.x, vehicle.y), bounds)[1],
                    "state": vehicle.state,
                }
                for vehicle in frame.vehicles
            ],
        }
        for frame in frames
    ]
    stats = sim.summary()
    return {
        "roads": roads,
        "frames": projected_frames,
        "stats": asdict(stats),
        "bounds": {
            "minX": bounds[0],
            "minY": bounds[1],
            "maxX": bounds[2],
            "maxY": bounds[3],
        },
    }


def _bounds(points: list[tuple[float, float]]) -> tuple[float, float, float, float]:
    min_x = min(point[0] for point in points)
    min_y = min(point[1] for point in points)
    max_x = max(point[0] for point in points)
    max_y = max(point[1] for point in points)
    return min_x, min_y, max_x, max_y


def _project_point(point: tuple[float, float], bounds: tuple[float, float, float, float]) -> tuple[float, float]:
    min_x, min_y, max_x, max_y = bounds
    width = max(max_x - min_x, 1e-9)
    height = max(max_y - min_y, 1e-9)
    padding = 48
    canvas_width = 1000
    canvas_height = 700
    x = padding + ((point[0] - min_x) / width) * (canvas_width - padding * 2)
    y = padding + (1 - ((point[1] - min_y) / height)) * (canvas_height - padding * 2)
    return round(x, 2), round(y, 2)


def _render_html(title: str, payload: dict[str, object]) -> str:
    data_json = json.dumps(payload, ensure_ascii=True, separators=(",", ":"))
    escaped_title = html.escape(title)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escaped_title}</title>
  <style>
    :root {{
      --bg: #f5f3ec;
      --ink: #20242a;
      --muted: #667071;
      --panel: #ffffff;
      --road: #74828f;
      --road-hot: #d64737;
      --road-mid: #df9c28;
      --vehicle: #0969da;
      --accent: #0f766e;
      --line: #d8d4c8;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background:
        linear-gradient(120deg, rgba(15, 118, 110, 0.08), transparent 35%),
        linear-gradient(280deg, rgba(214, 71, 55, 0.08), transparent 42%),
        var(--bg);
      color: var(--ink);
      font-family: Avenir Next, Trebuchet MS, Verdana, sans-serif;
    }}
    main {{
      display: grid;
      grid-template-columns: minmax(0, 1fr) 320px;
      gap: 18px;
      min-height: 100vh;
      padding: 18px;
    }}
    .map-shell {{
      min-height: calc(100vh - 36px);
      border: 1px solid var(--line);
      background: #fbfaf6;
      border-radius: 8px;
      overflow: hidden;
      position: relative;
    }}
    svg {{
      width: 100%;
      height: 100%;
      min-height: calc(100vh - 38px);
      display: block;
    }}
    .panel {{
      border: 1px solid var(--line);
      background: rgba(255, 255, 255, 0.86);
      border-radius: 8px;
      padding: 16px;
      align-self: start;
    }}
    h1 {{
      margin: 0 0 12px;
      font-size: 22px;
      line-height: 1.15;
      letter-spacing: 0;
    }}
    .metric {{
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 12px;
      padding: 10px 0;
      border-top: 1px solid var(--line);
      font-size: 14px;
    }}
    .metric span:first-child {{ color: var(--muted); }}
    .metric span:last-child {{ font-weight: 700; }}
    .controls {{
      display: grid;
      grid-template-columns: 44px 1fr;
      gap: 10px;
      align-items: center;
      margin: 14px 0 8px;
    }}
    button {{
      height: 38px;
      border: 1px solid #1f5f58;
      background: var(--accent);
      color: white;
      border-radius: 8px;
      font-size: 17px;
      cursor: pointer;
    }}
    input[type="range"] {{ width: 100%; }}
    .legend {{
      display: grid;
      gap: 8px;
      margin-top: 14px;
      color: var(--muted);
      font-size: 13px;
    }}
    .legend-row {{
      display: flex;
      align-items: center;
      gap: 8px;
    }}
    .swatch {{
      width: 24px;
      height: 4px;
      border-radius: 999px;
      background: var(--road);
    }}
    .swatch.mid {{ background: var(--road-mid); }}
    .swatch.hot {{ background: var(--road-hot); }}
    .swatch.vehicle {{
      width: 10px;
      height: 10px;
      border-radius: 999px;
      background: var(--vehicle);
    }}
    .road {{
      fill: none;
      stroke-linecap: round;
      stroke-linejoin: round;
      opacity: 0.88;
    }}
    .vehicle {{
      fill: var(--vehicle);
      stroke: white;
      stroke-width: 2;
      filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.22));
    }}
    .time-badge {{
      position: absolute;
      left: 16px;
      bottom: 16px;
      background: rgba(255, 255, 255, 0.9);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 8px 10px;
      font-size: 14px;
      font-weight: 700;
    }}
    @media (max-width: 860px) {{
      main {{ grid-template-columns: 1fr; }}
      .map-shell {{ min-height: 62vh; }}
      svg {{ min-height: 62vh; }}
    }}
  </style>
</head>
<body>
  <main>
    <section class="map-shell" aria-label="Traffic map">
      <svg id="map" viewBox="0 0 1000 700" role="img" aria-label="Road network and vehicles"></svg>
      <div class="time-badge" id="timeBadge">00:00</div>
    </section>
    <aside class="panel">
      <h1>{escaped_title}</h1>
      <div class="controls">
        <button id="playButton" title="Play or pause animation">></button>
        <input id="frameSlider" type="range" min="0" value="0" step="1">
      </div>
      <div class="metric"><span>Tick</span><span id="tickValue">0</span></div>
      <div class="metric"><span>Moving vehicles</span><span id="vehicleValue">0</span></div>
      <div class="metric"><span>Arrived vehicles</span><span id="arrivedValue">0</span></div>
      <div class="metric"><span>Average trip</span><span id="tripValue">0.00 min</span></div>
      <div class="metric"><span>Max road load</span><span id="loadValue">0.00</span></div>
      <div class="legend">
        <div class="legend-row"><span class="swatch"></span><span>low road load</span></div>
        <div class="legend-row"><span class="swatch mid"></span><span>medium road load</span></div>
        <div class="legend-row"><span class="swatch hot"></span><span>high road load</span></div>
        <div class="legend-row"><span class="swatch vehicle"></span><span>vehicle agents</span></div>
      </div>
    </aside>
  </main>
  <script>
    const data = {data_json};
    const svg = document.getElementById("map");
    const slider = document.getElementById("frameSlider");
    const playButton = document.getElementById("playButton");
    const timeBadge = document.getElementById("timeBadge");
    const tickValue = document.getElementById("tickValue");
    const vehicleValue = document.getElementById("vehicleValue");
    const arrivedValue = document.getElementById("arrivedValue");
    const tripValue = document.getElementById("tripValue");
    const loadValue = document.getElementById("loadValue");
    let frameIndex = 0;
    let timer = null;

    slider.max = Math.max(data.frames.length - 1, 0);
    renderRoads();
    renderFrame(0);

    playButton.addEventListener("click", () => {{
      if (timer) {{
        clearInterval(timer);
        timer = null;
        playButton.textContent = ">";
        return;
      }}
      playButton.textContent = "||";
      timer = setInterval(() => {{
        frameIndex = (frameIndex + 1) % data.frames.length;
        renderFrame(frameIndex);
      }}, 140);
    }});

    slider.addEventListener("input", () => {{
      frameIndex = Number(slider.value);
      renderFrame(frameIndex);
    }});

    function renderRoads() {{
      const group = document.createElementNS("http://www.w3.org/2000/svg", "g");
      group.setAttribute("id", "roads");
      for (const road of data.roads) {{
        const polyline = document.createElementNS("http://www.w3.org/2000/svg", "polyline");
        polyline.setAttribute("class", "road");
        polyline.setAttribute("points", road.points.map(point => point.join(",")).join(" "));
        polyline.setAttribute("stroke", roadColor(road.load, road.isOpen));
        polyline.setAttribute("stroke-width", String(2.5 + Math.min(road.load, 1.5) * 5));
        group.appendChild(polyline);
      }}
      svg.appendChild(group);
    }}

    function renderFrame(index) {{
      const frame = data.frames[index];
      slider.value = String(index);
      svg.querySelector("#vehicles")?.remove();
      const group = document.createElementNS("http://www.w3.org/2000/svg", "g");
      group.setAttribute("id", "vehicles");
      for (const vehicle of frame.vehicles) {{
        const circle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
        circle.setAttribute("class", "vehicle");
        circle.setAttribute("cx", vehicle.x);
        circle.setAttribute("cy", vehicle.y);
        circle.setAttribute("r", "6");
        group.appendChild(circle);
      }}
      svg.appendChild(group);
      tickValue.textContent = frame.tick;
      vehicleValue.textContent = frame.vehicles.length;
      arrivedValue.textContent = data.stats.arrived_vehicles;
      tripValue.textContent = `${{(data.stats.average_trip_time_s / 60).toFixed(2)}} min`;
      loadValue.textContent = data.stats.max_road_load.toFixed(2);
      timeBadge.textContent = formatTime(frame.simTimeS);
    }}

    function roadColor(load, isOpen) {{
      if (!isOpen) return "#222";
      if (load >= 0.65) return "#d64737";
      if (load >= 0.25) return "#df9c28";
      return "#74828f";
    }}

    function formatTime(seconds) {{
      const minutes = Math.floor(seconds / 60);
      const rest = Math.floor(seconds % 60);
      return `${{String(minutes).padStart(2, "0")}}:${{String(rest).padStart(2, "0")}}`;
    }}
  </script>
</body>
</html>
"""
