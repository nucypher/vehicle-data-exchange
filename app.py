import dash
import os
import shutil

external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

app = dash.Dash("NuCypher Vehicular Data Sharing Application", external_stylesheets=external_stylesheets)
server = app.server
app.config.suppress_callback_exceptions = True

# remove old data files and re-create data folder
shutil.rmtree('./data', ignore_errors=True)
os.mkdir("./data")

DB_FILE = './data/vehicle_sensors.db'
DB_NAME = 'VehicleData'

# vehicular properties
PROPERTIES = {'oil_temp': 'Oil Temperature (°C)',
              'intake_temp': 'Intake Temperature (°C)',
              'coolant_temp': 'Coolant Temperature (°C)',
              'rpm': 'Revolutions Per Minute',
              'speed': 'Speed (mph)',
              'throttle_pos': 'Throttle Position (%)',
              }
