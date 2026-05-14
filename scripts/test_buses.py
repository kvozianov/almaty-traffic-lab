import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))
from traffic_sim.graph_cache import load_preset_graph

graph = load_preset_graph("full_almaty_fast")

nodes = list(graph.nodes.values())
roads = list(graph.roads.values())
print("Total nodes:", len(nodes))
print("Total roads:", len(roads))
