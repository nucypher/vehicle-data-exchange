import dash
import os
import shutil
from nucypher_helper import KFRAGS_FOLDER
from demo_keys import KEYS_FOLDER

external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

app = dash.Dash("NuCypher Vehicular Data Sharing Application", external_stylesheets=external_stylesheets)
server = app.server
app.config.suppress_callback_exceptions = True

# remove old kfrag files and re-create folder
shutil.rmtree(KFRAGS_FOLDER, ignore_errors=True)
os.mkdir(KFRAGS_FOLDER)

# remove old key files and re-create folder
shutil.rmtree(KEYS_FOLDER, ignore_errors=True)
os.mkdir(KEYS_FOLDER)

# remove old data files and re-create folder
shutil.rmtree('./data', ignore_errors=True)
os.mkdir("./data")

DB_FILE = './data/vehicle_sensors.db'
DB_NAME = 'VehicleData'

# OBD properties
PROPERTIES = {'engineOn': 'Engine Status',
              'temp': 'Temperature (°C)',
              'rpm': 'Revolutions Per Minute',
              'vss': 'Vehicle Speed',
              'maf': 'Mass AirFlow',
              'throttlepos': 'Throttle Position (%)',
              'lat': 'Latitude (°)',
              'lon': 'Longitude (°)',
              'alt': 'Alternator Voltage',
              'gpsSpeed': 'GPS Speed',
              'course': 'Course',
              'gpsTime': "GPS Timestamp"
              }
