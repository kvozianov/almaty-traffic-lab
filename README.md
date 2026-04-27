# AI Traffic Digital Twin (Almaty)

Research-oriented project for simulating Almaty traffic on a real road graph with scenario analysis:

- accidents that reduce road capacity
- road repairs that close roads
- traffic light timing changes
- bypass road additions
- time-of-day demand and speed profiles
- AI-style driver policy for trip choice and rerouting behavior
- traffic data provider adapters for synthetic, CSV, Yandex, and 2GIS

The app runs locally with Python + FastAPI. OpenStreetMap is the default road graph source, Leaflet is the no-key map fallback, and 2GIS MapGL can be enabled for 3D visualization when a `2GIS_API_KEY` is available.

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
- `traffic_sim.ai_policy`: driver policy layer
- `traffic_sim.time_profiles`: time-of-day speed and demand profiles
- `traffic_sim.traffic_providers`: synthetic/CSV/Yandex/2GIS traffic adapters
- `traffic_sim.web_app`: FastAPI dashboard API
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

Useful dashboard features:

- city-wide fast preview for Full Almaty
- smooth animated vehicle playback
- route-based mass preview with procedural vehicles moving from road to road
- adaptive canvas rendering with FPS and visible/drawn vehicle metrics
- random road-based vehicle spawn points
- AI policy mode: heuristic now, LLM adapter interface for later
- manual or automatic time of day
- scenario editor: accident, repair, closure, capacity reduction, signal delay, demand surge, weather, bypass road
- road detail panel with capacity, lanes, speed, class, and provider observations
- JSON metrics and CSV road-load exports

Optional environment variables:

```bash
export TRAFFIC_SIM_MAP_PROVIDER=leaflet
export TRAFFIC_DATA_PROVIDER=synthetic
export TRAFFIC_SIM_DEFAULT_TIME=17:00
export TRAFFIC_SIM_POLICY=heuristic
export 2GIS_API_KEY=your_2gis_key
export YANDEX_MAPS_API_KEY=your_yandex_key
```

Without API keys the project still works with Leaflet + synthetic traffic profiles. Yandex and 2GIS adapters intentionally do not scrape or store raw traffic data; use official APIs/layers or imported CSV data.

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

The web dashboard includes OSM tiles, road-load heat coloring, animated vehicles, clickable scenario roads, before/after comparison, time profiles, traffic data provider status, and JSON/CSV exports.

The `--bbox` arguments are ordered as:

```text
NORTH SOUTH EAST WEST
```

This smaller bbox was verified during development and is a good first real-map run before scaling up to larger parts of Almaty.

## Research data files

- `data/time_profiles/almaty_weekday.json`: synthetic weekday demand/speed profile
- `data/corridors/almaty_major_roads.json`: named Almaty corridors for statistics
- `data/traffic_profiles/sample_almaty.csv`: sample traffic observations
- `data/scenarios/examples.json`: reproducible demo scenarios
- `docs/figma/dashboard_screens.md`: 5-screen Figma design brief

## Suggested next steps

1. Add a real 2GIS API key and switch the dashboard to MapGL 3D.
2. Import manually collected traffic CSVs for Al-Farabi, Abay, Tole Bi, and Ryskulov.
3. Calibrate capacity and signal timing against known rush-hour behavior.
4. Connect an OpenAI-compatible policy provider for zone-level destination choice.
5. Create screenshots/GIFs and research scenarios for GitHub.
