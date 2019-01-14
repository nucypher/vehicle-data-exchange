from dash.dependencies import Output, Input, State, Event
from dash_table_experiments import DataTable
import dash_core_components as dcc
import dash_html_components as html
import json
import pandas as pd
import sqlite3
import time

from app import app, DB_FILE, DB_NAME
import car_session

layout = html.Div([
    html.Div([
        html.Img(src='./assets/nucypher_logo.png'),
    ], className='banner'),
    html.Div([
        html.Div([
            html.Div([
                html.Img(src='./assets/enrico.png', style={'height': '150px', 'width': '220px'}),
            ], className='two columns'),
            html.Div([
                html.Div([
                    html.H2('ENRICO'),
                    html.P("Enrico is the OBD device in Alicia's vehicle that uses a data policy key "
                           "to encrypt Alicia's vehicular measurements into a database or some storage service "
                           "(e.g., IPFS, S3, whatever). Data Sources like the OBD device remain "
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
        #dcc.Interval(id='gen-sensor-update', interval=1000, n_intervals=0),
    ], className='row'),
    html.Hr(),
    html.Div([
        html.H3('Encrypted OBD Data in Database'),
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
    [#Event('gen-sensor-update', 'interval'),
     Event('generate-button', 'click')]
)
def generate_vehicular_data(gen_time, policy_pubkey_hex, last_readings):
    if int(gen_time) == 0:
        # button has not been clicked as yet or interval triggered before click
        return None

    pub_key_bytes = bytes.fromhex(policy_pubkey_hex)
    latest_readings = car_session.reproduce_stored_session(pub_key_bytes,
                                                           save_as_file=True,
                                                           store_in_db=True,
                                                           send_by_mqtt=False)
    return latest_readings


@app.callback(
    Output('db-table-content', 'children'),
    [Input('cached-last-readings', 'children')]
)
def display_vehicular_data(last_readings):
    print("LAST", last_readings)
    if last_readings is None:
        # button hasn't been clicked as yet
        return ''

    now = time.time()
    duration = 30  # last 30s of readings
    db_conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query('SELECT Timestamp, EncryptedData '
                           'FROM {} '
                           #'WHERE Timestamp > "{}" AND Timestamp <= "{}" '
                           'ORDER BY Timestamp DESC;'
                           .format(DB_NAME), #, now - duration, now),
                           db_conn)
    rows = df.to_dict('rows')

    return html.Div([
        html.Div(id='datatable-output'),
        DataTable(
            id='datatable',
            rows=rows,
        )
    ])
