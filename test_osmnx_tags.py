import osmnx as ox
# Add turn restrictions and other useful tags
ox.settings.useful_tags_way = ox.settings.useful_tags_way + ['turn:lanes', 'turn:lanes:forward', 'turn:lanes:backward', 'maxspeed:forward', 'maxspeed:backward']
print(ox.settings.useful_tags_way)
