import pymysql
import pymysql.cursors
from math import radians, cos, sin, sqrt, atan2
import folium
import requests
import polyline

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

  SELECT thing_id, trace_date, latitude, longitude, altitude, hdop ,speed,gprmc_heading_deg, engine_status
  FROM trace_week
    WHERE thing_id = 3278 AND trace_date_day = '2024-03-02'
 ORDER BY date_insertion
    """)


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
for row in cursor.fetchall():
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





tourne_1 = tournes[0]  # Assuming tourne 1 is the first tourne in the list

# print (tourne_1)

######################################################################################################
import osmnx as ox

# Load the .osm file as a graph
G = ox.graph_from_xml(r'C:\GraphHopper\algeria-latest.osm')

# Save the graph to .graphml
ox.save_graphml(G, r'C:\GraphHopper\algeria-latest.osm.graphml')

# Load the .graphml file
g2 = ox.load_graphml(r'C:\GraphHopper\algeria-latest.osm.graphml')

# Plot the graph
ox.plot_graph(g2)

