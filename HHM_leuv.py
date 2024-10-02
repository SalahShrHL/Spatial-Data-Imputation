####################### dead reck using distance################################################
import math
from datetime import datetime, timedelta
import folium
import pymysql
import pymysql.cursors
import osmnx as ox
import networkx as nx

# Connect to the database
connection = pymysql.connect(
    host='localhost',
    port=3306,  # Port should be specified separately from the host
    user='root',
    password='123456',
    database='geopfe'
)

try:
    with connection.cursor(pymysql.cursors.DictCursor) as cursor:
        cursor.execute("""
            SELECT thing_id, trace_date, latitude, longitude, altitude, speed, engine_status
            FROM trace_week
            WHERE thing_id = 3278 AND trace_date_day = '2024-03-02'
            ORDER BY trace_date
        """)
        rows = cursor.fetchall()  # Fetch the data within the try block

finally:
    # Close the connection
    connection.close()

######################################################################################
# Initialize list to store tournes
tournes = []

# Initialize variables to store current tourne data
current_tourne = []
current_engine_status = None

# Iterate over the fetched rows
for row in rows:
    # Check if engine_status has changed
    if row['engine_status'] != current_engine_status:
        # If engine_status is 1 (active), start a new tourne
        if row['engine_status'] == 1:
            current_tourne = []  # Start a new tourne
            current_tourne.append(row)  # Add current row to the new tourne
            tournes.append(current_tourne)  # Append new tourne to the list of tournes
        # If engine_status is 0 (inactive) and current tourne is not empty, end the current tourne
        elif row['engine_status'] == 0 and current_tourne:
            current_tourne = []  # Clear the current tourne
    # If engine_status remains the same, continue adding points to the current tourne
    elif current_tourne:
        current_tourne.append(row)  # Add current row to the current tourne

    # Update current engine_status for the next iteration
    current_engine_status = row['engine_status']

# Function to convert speed from km/h to m/s
def kmh_to_ms(speed_kmh):
    return speed_kmh * 1000 / 3600

# Function to calculate the distance between two points using the Haversine formula
def haversine(coord1, coord2):
    R = 6371000  # Radius of the Earth in meters

    lat1, lon1 = coord1
    lat2, lon2 = coord2

    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    distance = R * c

    return distance

# Function to calculate the bearing between two points
def calculate_bearing(coord1, coord2):
    lat1, lon1 = coord1
    lat2, lon2 = coord2

    # Convert coordinates from degrees to radians
    lat1 = math.radians(lat1)
    lon1 = math.radians(lon1)
    lat2 = math.radians(lat2)
    lon2 = math.radians(lon2)

    # Calculate differences in longitude
    dlon = lon2 - lon1

    # Calculate the bearing
    x = math.sin(dlon) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - (math.sin(lat1) * math.cos(lat2) * math.cos(dlon))
    initial_bearing = math.atan2(x, y)

    # Convert the bearing from radians to degrees
    initial_bearing = math.degrees(initial_bearing)
    
    # Normalize the bearing to be between 0° and 360°
    compass_bearing = (initial_bearing + 360) % 360

    return compass_bearing

# Fonction pour calculer la nouvelle position
def calculate_new_position(lat, lon, distance, bearing):
    R = 6371000  # Rayon de la Terre en mètres

    # Convertir l'orientation en radians
    bearing = math.radians(bearing)
    # Convertir les coordonnées initiales de degrés à radians
    lat1 = math.radians(lat)
    lon1 = math.radians(lon)

    # Calculer la distance angulaire parcourue
    delta = distance / R

    # Appliquer les formules pour calculer la nouvelle position
    new_lat = math.asin(math.sin(lat1) * math.cos(delta) + math.cos(lat1) * math.sin(delta) * math.cos(bearing))
    new_lon = lon1 + math.atan2(math.sin(bearing) * math.sin(delta) * math.cos(lat1), math.cos(delta) - math.sin(lat1) * math.sin(new_lat))

    # Convertir les nouvelles coordonnées de radians à degrés
    new_lat = math.degrees(new_lat)
    new_lon = math.degrees(new_lon)

    return new_lat, new_lon



# Distance interval in meters
distance_interval = 40




# Select the specific tourne
tourne_1 = tournes[3]

# Initialize the list of GPS traces and estimated positions
gps_traces = [(float(d['latitude']), float(d['longitude'])) for d in tourne_1]
estimated_positions = []

# Process the GPS data for the current tourne
for i in range(len(tourne_1) - 1):
    current_position = (float(tourne_1[i]['latitude']), float(tourne_1[i]['longitude']))
    next_position = (float(tourne_1[i + 1]['latitude']), float(tourne_1[i + 1]['longitude']))
    speed_kmh = tourne_1[i]['speed']  # Speed in km/h
    speed_ms = kmh_to_ms(speed_kmh)  # Convert speed to m/s

    bearing = calculate_bearing(current_position, next_position)

    current_time = tourne_1[i]['trace_date']
    next_time = tourne_1[i + 1]['trace_date']

    # Calculate the distance between current and next position
    segment_distance = haversine(current_position, next_position)

    # Generate points if the segment distance is greater than the distance interval
    if segment_distance > distance_interval:
        while segment_distance > distance_interval:
            if speed_ms > 0:
                current_time += timedelta(seconds=(distance_interval / speed_ms))
            current_position = calculate_new_position(current_position[0], current_position[1], distance_interval, bearing)
            estimated_positions.append((current_time, current_position))
            segment_distance -= distance_interval

# Combine the GPS traces and estimated positions while maintaining the order
combined_traces = []
estimated_index = 0

for i in range(len(tourne_1) - 1):
    combined_traces.append((tourne_1[i]['trace_date'], (float(tourne_1[i]['latitude']), float(tourne_1[i]['longitude']))))
    # Insert estimated positions between the original points
    while estimated_index < len(estimated_positions) and estimated_positions[estimated_index][0] < tourne_1[i + 1]['trace_date']:
        combined_traces.append(estimated_positions[estimated_index])
        estimated_index += 1

# Add the last point from tourne_1
combined_traces.append((tourne_1[-1]['trace_date'], (float(tourne_1[-1]['latitude']), float(tourne_1[-1]['longitude']))))

# Update gps_traces to include both original and estimated points
gps_traces = [trace[1] for trace in combined_traces]







######################################################################################### try just with original points
#########################################################################################
#########################################################################################



# tourne_1= tournes[3]
# gps_traces = [(float(d['latitude']), float(d['longitude'])) for d in tourne_1]


# # # Select the specific tourne
# # tourne_1 = tournes[7]

# # Initialize the list of new positions
# estimated_positions = []

# # Process the GPS data for the current tourne
# for i in range(len(tourne_1) - 1):
#     current_position = (float(tourne_1[i]['latitude']), float(tourne_1[i]['longitude']))
#     next_position = (float(tourne_1[i + 1]['latitude']), float(tourne_1[i + 1]['longitude']))
#     speed_kmh = tourne_1[i]['speed']  # Speed in km/h
#     speed_ms = kmh_to_ms(speed_kmh)  # Convert speed to m/s

#     bearing = calculate_bearing(current_position, next_position)

#     current_time = tourne_1[i]['trace_date']
#     next_time = tourne_1[i + 1]['trace_date']

#     # Calculate the distance between current and next position
#     segment_distance = haversine(current_position, next_position)

#     # Generate points if the segment distance is greater than the distance interval
#     if segment_distance > distance_interval:
#         while segment_distance > distance_interval:
#             if speed_ms > 0:
#                 current_time += timedelta(seconds=(distance_interval / speed_ms))
#             current_position = calculate_new_position(current_position[0], current_position[1], distance_interval, bearing)
#             estimated_positions.append((current_time,current_position ))
#             segment_distance -= distance_interval

######################################################################################### Generate multiple files
#########################################################################################
#########################################################################################



# # Iterate over all tournes and process each one
# for index, tourne in enumerate(tournes):
#     # Initialize the list of new positions
#     estimated_positions = []

#     # Process the GPS data for the current tourne
#     for i in range(len(tourne) - 1):
#         current_position = (float(tourne[i]['latitude']), float(tourne[i]['longitude']))
#         next_position = (float(tourne[i + 1]['latitude']), float(tourne[i + 1]['longitude']))
#         speed_kmh = tourne[i]['speed']  # Speed in km/h
#         speed_ms = kmh_to_ms(speed_kmh)  # Convert speed to m/s

#         bearing = calculate_bearing(current_position, next_position)

#         current_time = tourne[i]['trace_date']
#         next_time = tourne[i + 1]['trace_date']

#         # Calculate the distance between current and next position
#         segment_distance = haversine(current_position, next_position)

#         # Generate points if the segment distance is greater than the distance interval
#         # Generate points if the segment distance is greater than the distance interval
#         if segment_distance > distance_interval:
#             while segment_distance > distance_interval:
#                 if speed_ms > 0:
#                     current_time += timedelta(seconds=(distance_interval / speed_ms))
#                 current_position = calculate_new_position(current_position[0], current_position[1], distance_interval, bearing)
#                 estimated_positions.append((current_time, current_position))
#                 segment_distance -= distance_interval


    # Create a map centered around the first point of the current tourne
    # map_center = (float(tourne[0]['latitude']), float(tourne[0]['longitude']))

    # # Map before applying dead reckoning
    # original_map = folium.Map(location=map_center, zoom_start=15)
    # for i, point in enumerate(tourne, start=1):
    #     folium.Marker(
    #         location=(float(point['latitude']), float(point['longitude'])),
    #         popup=f"Point Number: {i}",  # Display point number
    #         icon=folium.Icon(color='green', icon='car', prefix='fa')
    #     ).add_to(original_map)
    # original_map_filename = f"C:\\Users\\SALAHPC\\Desktop\\fin\\dead\\map_tourne_{index + 1}_original.html"
    # original_map.save(original_map_filename)
    # print(f"Original map for tourne {index + 1} saved as {original_map_filename}")

    # # Map after applying dead reckoning
    # estimated_map = folium.Map(location=map_center, zoom_start=15)
    # for i, point in enumerate(tourne, start=1):
    #     folium.Marker(
    #         location=(float(point['latitude']), float(point['longitude'])),
    #         popup=f"Point Number: {i}",  # Display point number
    #         icon=folium.Icon(color='green', icon='car', prefix='fa')
    #     ).add_to(estimated_map)
    # for i, (estimated_time, estimated_point) in enumerate(estimated_positions, start=len(tourne)+1):
    #     folium.Marker(
    #         location=estimated_point,  # The latitude and longitude of the point
    #         popup=f"Point Number: {i}\nEstimated Time: {estimated_time}",
    #         icon=folium.Icon(color='purple', icon='car', prefix='fa')  # Font Awesome car icon
    #     ).add_to(estimated_map)  # Add the marker to the map
    # estimated_map_filename = f"C:\\Users\\SALAHPC\\Desktop\\fin\\dead\\dist\\map_tourne_{index + 1}_estimated.html"
    # estimated_map.save(estimated_map_filename)
    # print(f"Estimated map for tourne {index + 1} saved as {estimated_map_filename}")




###########################################################################################
###########################################################################################
###########################################################################################



from leuvenmapmatching.map.inmem import InMemMap
from leuvenmapmatching.matcher.distance import DistanceMatcher
from leuvenmapmatching.visualization import plot_map
import osmnx as ox
import geopandas as gpd
###############################################################

# place_name = "Algiers, Algeria"  # Specify your area of interest
# graph = ox.graph_from_place(place_name, network_type='drive', simplify=False)

# import osmnx as ox




# Extract all latitudes and longitudes from gps_traces
latitudes = [trace[0] for trace in gps_traces]
longitudes = [trace[1] for trace in gps_traces]

# Define the latitude and longitude boundaries
# Define a buffer to expand the bounding box (in degrees)
buffer = 0.01  # Adjust this value as needed

# Define the latitude and longitude boundaries
north = max(latitudes) + buffer
south = min(latitudes) - buffer
east = max(longitudes) + buffer
west = min(longitudes) - buffer

# Get the graph for the specified area
G = ox.graph_from_bbox(north, south, east, west, network_type='drive',simplify=True)
# G = ox.graph_from_bbox(north, south, east, west,network_type='all', simplify=False)

graph_proj = ox.project_graph(G)

# Continue with your code...
# gdf_nodes, gdf_edges = ox.graph_to_gdfs(G)
map_con = InMemMap("my_map", use_latlon=False, use_rtree=True, index_edges=True)


nodes, edges = ox.graph_to_gdfs(graph_proj, nodes=True, edges=True)
nodes_proj = nodes.to_crs("EPSG:3395")
edges_proj = edges.to_crs("EPSG:3395")
for nid, row in nodes_proj.iterrows():
    map_con.add_node(nid, (row['lat'], row['lon']))
# We can also extract edges also directly from networkx graph
for nid1, nid2, _ in G.edges:
    map_con.add_edge(nid1, nid2)


#############################################################


# matcher = DistanceMatcher(map_con, max_dist=0.02, obs_noise=0.05, min_prob_norm=0.5, max_lattice_width=5)
# matcher = DistanceMatcher(map_con, max_dist_init=2, obs_noise=1, obs_noise_ne=5,
#                           non_emitting_states=True, only_edges=True , max_lattice_width=5)

matcher = DistanceMatcher(map_con, max_dist_init=0.02, obs_noise=1, obs_noise_ne=5,
                          non_emitting_states=False, only_edges=False, max_lattice_width=10)

# matcher = DistanceMatcher(map_con,
#                          max_dist=100, max_dist_init=25,  # meter
#                          min_prob_norm=0.001,
#                          non_emitting_length_factor=0.75,
#                          obs_noise=50, obs_noise_ne=75,  # meter
#                          dist_noise=50,  # meter
#                          non_emitting_states=True,
#                          max_lattice_width=5)

# states, _ = matcher.match(gps_traces)
nodes = matcher.path_pred_onlynodes



states, _ = matcher.match(gps_traces)

# Get the matched nodes
matched_nodes = [state[1] for state in states]

# Get the latitude and longitude of the matched nodes
matched_coords = [map_con.node_coordinates(node) for node in matched_nodes]
# print(matched_coords)

############################################################# Graphhoper
import requests

# Generate GPX content
gpx_content = '<?xml version="1.0" encoding="UTF-8"?>\n'
gpx_content += '<gpx version="1.1" creator="GraphHopper">\n<trk><name>GPS Data</name><trkseg>\n'
for point in matched_coords:
    gpx_content += f'    <trkpt lat="{point[0]}" lon="{point[1]}"></trkpt>\n'
gpx_content += '</trkseg></trk></gpx>'

# GraphHopper API URL
url = 'http://localhost:8989/match?profile=car&locale=en&points_encoded=false'

# Send a POST request to the API
response = requests.post(url, data=gpx_content, headers={'Content-Type': 'application/xml'})

if response.status_code != 200:
    print("Request data:", gpx_content)  # Log the GPX content
    print("Response content:", response.content)  # Log the response content
    raise RuntimeError(f"GraphHopper API request failed with status code {response.status_code}")

data = response.json()

# Check if 'paths' is in the response
if 'paths' not in data or not data['paths']:
    raise KeyError("'paths' not found in the API response")

# Extract the matched route
route = data['paths'][0]['points']['coordinates']

# Create a Folium map
# m = folium.Map(location=[route[0][1], route[0][0]], zoom_start=13)



# Create a Folium map with a less clear background using Stamen Toner Lite tiles
m = folium.Map(location=[route[0][1], route[0][0]], zoom_start=13)

folium.PolyLine([(point[1], point[0]) for point in route], color='#1E90FF', weight=5).add_to(m)


# m = folium.Map(location=[route[0][1], route[0][0]], zoom_start=13)

# # Add Stamen Toner Lite tile layer with attribution
# folium.TileLayer(
#     tiles='https://stamen-tiles.a.ssl.fastly.net/toner-lite/{z}/{x}/{y}.png',
#     attr='Map tiles by <a href="http://stamen.com">Stamen Design</a>, '
#          'under <a href="http://creativecommons.org/licenses/by/3.0">CC BY 3.0</a>. '
#          'Data by <a href="http://openstreetmap.org">OpenStreetMap</a>, '
#          'under ODbL.'
# ).add_to(m)
# Add the route to the map with a bright color (cyan)

# Add markers for the start and end points with custom icons
start_point = route[0]
end_point = route[-1]

folium.Marker(
    location=[start_point[1], start_point[0]],
    popup="Start",
    icon=folium.Icon(icon='car', color='red', prefix='fa')
).add_to(m)

folium.Marker(
    location=[end_point[1], end_point[0]],
    popup="End",
    icon=folium.Icon(icon='stop', color='red', prefix='fa')
).add_to(m)
# Save the map to an HTML file
m.save(r'C:\Users\SALAHPC\Desktop\fin\dead\graphopper\map.html')







############################################################# visualization

from leuvenmapmatching import visualization as mmviz

mmviz.plot_map(map_con, matcher=matcher,
                use_osm=True, zoom_path=True,
                show_labels=False, show_matching=True, show_graph=False,
                filename="C:\\Users\\SALAHPC\\Desktop\\fin\\dead\\my_osm_plot.png")

##########



import matplotlib.pyplot as plt
fig, ax = plt.subplots(1, 1)
plot_map(map_con, matcher=matcher, ax=ax,
               show_labels=False, show_matching=True, show_graph=True,
                )
# # # filename="my_plot.png"
plt.show()