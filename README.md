# Traffic Simulation (Almaty MVP)

Research-oriented project for simulating city traffic on a road graph with scenario analysis:

- accidents that reduce road capacity
- road repairs that close roads
- traffic light timing changes
- bypass road additions

The first version is intentionally lightweight. Core simulation logic runs on the Python standard library, and OpenStreetMap integration is available as an optional next step through `osmnx`.

## Project goals

- represent a city as a directed weighted graph
- simulate vehicles moving step by step through the graph
- measure congestion, travel time, and road load
- compare traffic conditions before and after a scenario

## Current architecture

```text
city graph -> route planning -> vehicle agents -> tick simulation -> metrics
```

Main modules:

- `traffic_sim.models`: domain entities
- `traffic_sim.network`: road graph and routing
- `traffic_sim.simulation`: tick-based traffic engine
- `traffic_sim.scenarios`: road events and interventions
- `traffic_sim.cli`: demo runner

## Quick start

Create and activate a virtual environment if you want an isolated setup:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install the package locally:

```bash
pip install -e .
```

Run the demo simulation:

```bash
traffic-sim --vehicles 40 --steps 180 --scenario accident
```

Without installation you can also run:

```bash
PYTHONPATH=src python3 -m traffic_sim.cli --vehicles 40 --steps 180 --scenario accident
```

Run tests:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests
```

Generate an animated HTML visualization:

```bash
PYTHONPATH=src python3 -m traffic_sim.visualize_cli \
  --vehicles 40 \
  --steps 180 \
  --scenario accident \
  --output reports/demo.html
```

Run a real-time desktop window:

```bash
PYTHONPATH=src python3 -m traffic_sim.live_cli \
  --vehicles 40 \
  --steps 180 \
  --scenario accident
```

Run the production web dashboard:

```bash
traffic-sim-web --host 127.0.0.1 --port 8000
```

Then open:

```text
http://127.0.0.1:8000
```

## Optional OSM integration

To prepare the project for real city data:

```bash
pip install -e .[osm]
```

Then you can use `traffic_sim.network.load_graph_from_osm_place(...)` inside the code to convert a drivable OpenStreetMap graph into the internal simulation graph.

Example with a real district from Almaty:

```bash
.venv/bin/python -m traffic_sim.cli \
  --source place \
  --place "Almaly District, Almaty, Kazakhstan" \
  --vehicles 60 \
  --steps 180
```

Example with a bounded area near central Almaty:

```bash
.venv/bin/python -m traffic_sim.cli \
  --source bbox \
  --bbox 43.245 43.240 76.950 76.940 \
  --vehicles 60 \
  --steps 180
```

Generate the same real-map area as an animated report:

```bash
.venv/bin/python -m traffic_sim.visualize_cli \
  --source bbox \
  --bbox 43.245 43.240 76.950 76.940 \
  --vehicles 30 \
  --steps 120 \
  --output reports/almaty-center.html
```

Run the same real-map area in a live desktop window:

```bash
.venv/bin/python -m traffic_sim.live_cli \
  --source bbox \
  --bbox 43.245 43.240 76.950 76.940 \
  --vehicles 30 \
  --steps 120 \
  --fps 12
```

The web dashboard includes OSM tiles, road-load heat coloring, animated vehicles, clickable scenario roads, before/after comparison, and JSON/CSV exports.

The `--bbox` arguments are ordered as:

```text
NORTH SOUTH EAST WEST
```

This smaller bbox was verified during development and is a good first real-map run before scaling up to larger parts of Almaty.

## Suggested next steps

1. Load a bounded area of Almaty from OpenStreetMap.
2. Add a simple map visualization.
3. Introduce traffic demand from CSV or generated OD pairs.
4. Calibrate road capacity and signal timing.
5. Add analytics plots and scenario comparison reports.
