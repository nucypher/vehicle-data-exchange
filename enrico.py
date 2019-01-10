from dash.dependencies import Output, Input, State, Event
from dash_table_experiments import DataTable
import dash_core_components as dcc
import dash_html_components as html
import json
import pandas as pd
import random
import sqlite3
import time
from umbral import pre
from umbral.keys import UmbralPublicKey

from app import app, DB_FILE, DB_NAME, PROPERTIES

layout = html.Div([
    html.Div([
        html.Img(src='./assets/nucypher_logo.png'),
    ], className='banner'),
    html.Div([
        html.Div([
            html.Div([
                html.Img(src='./assets/enrico.png', style={'height': '170px', 'width': '240px'}),
            ], className='two columns'),
            html.Div([
                html.Div([
                    html.H2('ENRICO'),
                    html.P("Enrico is the Vehicle that uses a data policy key to encrypt Alicia's "
                           "vehicular measurements into a database or some storage service "
                           "(e.g., IPFS, S3, whatever). Data Sources like the Vehicle remain "
                           "completely unaware of the recipients. In their mind, they are producing data "
                           "for Alicia. "),
                ], className="row")
            ], className='five columns'),
        ], className='row'),
    ], className='app_name'),
    html.Hr(),
    html.H3('Data Policy'),
    html.Div([
        html.Div('Policy Key (hex): ', className='two columns'),
        dcc.Input(id='policy-pub-key', type='text', className='seven columns'),
        html.Button('Start Monitoring', id='generate-button', type='submit',
                    className="button button-primary", n_clicks_timestamp='0'),
        dcc.Interval(id='gen-sensor-update', interval=1000, n_intervals=0),
    ], className='row'),
    html.Hr(),
    html.Div([
        html.H3('Encrypted Vehicular Data into Database'),
        html.Div([
            html.Div('Latest Vehicle Data: ', className='two columns'),
            html.Div(id='cached-last-readings', className='two columns'),
        ], className='row'),
        html.Br(),
        html.Div(id='db-table-content'),
    ], className='row'),
])


@app.callback(
    Output('cached-last-readings', 'children'),
    [],
    [State('generate-button', 'n_clicks_timestamp'),
     State('policy-pub-key', 'value'),
     State('cached-last-readings', 'children')],
    [Event('gen-sensor-update', 'interval'),
     Event('generate-button', 'click')]
)
def generate_vehicular_data(gen_time, policy_pubkey_hex, last_readings):
    if int(gen_time) == 0:
        # button has not been clicked as yet or interval triggered before click
        return None

    sensor_readings = dict()
    if last_readings is None:
        # generate readings
        property_list = list(PROPERTIES.keys())
        sensor_readings[property_list[0]] = random.randrange(180, 230)
        sensor_readings[property_list[1]] = random.randrange(95, 115)
        sensor_readings[property_list[2]] = random.randrange(170, 220)
        sensor_readings[property_list[3]] = random.randrange(1000, 9500)
        sensor_readings[property_list[4]] = random.randrange(30, 140)
        sensor_readings[property_list[5]] = random.randrange(10, 90)
    else:
        last_sensor_readings = json.loads(last_readings)
        for key in last_sensor_readings.keys():
            sensor_readings[key] = last_sensor_readings[key] + random.uniform(-1, 1)

    latest_readings = json.dumps(sensor_readings)
    policy_pubkey = UmbralPublicKey.from_bytes(bytes.fromhex(policy_pubkey_hex))
    ciphertext, capsule = pre.encrypt(policy_pubkey, latest_readings.encode('utf-8'))

    timestamp = time.time()
    df = pd.DataFrame.from_dict({
        'Timestamp': [timestamp],
        'Data': [ciphertext.hex()],
        'Capsule': [capsule.to_bytes().hex()]
    })

    # add new vehicle data
    db_conn = sqlite3.connect(DB_FILE)
    df.to_sql(name=DB_NAME, con=db_conn, index=False, if_exists='append')

    print('Added vehicle sensor readings to db: ', latest_readings)
    return latest_readings


@app.callback(
    Output('db-table-content', 'children'),
    [Input('cached-last-readings', 'children')]
)
def display_vehicular_data(last_readings):
    if last_readings is None:
        # button hasn't been clicked as yet
        return ''

    now = time.time()
    duration = 30  # last 30s of readings
    db_conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query('SELECT Timestamp, Data, Capsule '
                           'FROM {} '
                           'WHERE Timestamp > "{}" AND Timestamp <= "{}" '
                           'ORDER BY Timestamp DESC;'
                           .format(DB_NAME, now - duration, now), db_conn)
    rows = df.to_dict('rows')

    return html.Div([
        html.Div(id='datatable-output'),
        DataTable(
            id='datatable',
            rows=rows,
        )
    ])
