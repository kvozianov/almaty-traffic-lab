import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))
from traffic_sim.zones import load_zones, load_od_matrix, build_zone_index

zones = load_zones()
print([z.zone_id for z in zones])

od_matrix = load_od_matrix()
print(od_matrix.keys())
