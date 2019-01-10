from dash.dependencies import Output, Input, State, Event
import dash_core_components as dcc
import dash_html_components as html
import demo_keys
import json
import nucypher_helper
import pandas as pd
import plotly.graph_objs as go
from plotly.graph_objs.layout import Margin
import sqlite3
import time
from umbral import pre, config

from app import app, DB_FILE, DB_NAME, PROPERTIES


layout = html.Div([
    html.Div([
        html.Img(src='./assets/nucypher_logo.png'),
    ], className='banner'),
    html.Div([
        html.Div([
            html.Div([
                html.Img(src='./assets/bob.png'),
            ], className='two columns'),
            html.Div([
                html.Div([
                    html.H2('INSURER BOB'),
                    html.P(
                        "Dr. Bob is Alicia's Insurance Company and will be granted access by Alicia "
                        "to access the encrypted vehicle data database and requests a re-encrypted ciphertext for "
                        "each set of timed measurements, which can then be decrypted using the Insurance company's "
                        "private key."),
                ], className="row")
            ], className='five columns'),
        ], className='row'),
    ], className='app_name'),
    html.Hr(),
    html.Button('Generate Key Pair',
                id='gen-key-button',
                type='submit',
                className='button button-primary'),
    html.Div([
        html.Div('Public Key:', className='two columns'),
        html.Div(id='pub-key', className='seven columns'),
    ], className='row'),
    html.Hr(),
    html.Div([
        html.H3('Vehicle Data from Encrypted DB'),
        html.Div([
            html.Button('Read Measurements', id='read-button', type='submit',
                        className='button button-primary', n_clicks_timestamp='0'),
        ], className='row'),
        html.Div(children=html.Div(id='measurements'), className='row'),
        dcc.Interval(id='measurements-update', interval=1000, n_intervals=0),
    ], className='row'),
    # Hidden div inside the app that stores previously decrypted measurements
    html.Div(id='latest-decrypted-measurements', style={'display': 'none'})
])


@app.callback(
    Output('latest-decrypted-measurements', 'children'),
    [],
    [State('read-button', 'n_clicks_timestamp'),
     State('latest-decrypted-measurements', 'children')],
    [Event('measurements-update', 'interval'),
     Event('read-button', 'click')]
)
def update_cached_decrypted_measurements_list(read_time, df_json_latest_measurements):
    if int(read_time) == 0:
        # button never clicked but triggered by interval
        return None

    df = pd.DataFrame()
    if df_json_latest_measurements is not None:
        df = pd.read_json(df_json_latest_measurements, convert_dates=False)
        # sort readings and order by timestamp
        df = df.sort_values(by='timestamp')

    last_timestamp = time.time() - 30  # last 30s
    if len(df) > 0:
        # use last timestamp
        last_timestamp = df['timestamp'].iloc[-1]

    db_conn = sqlite3.connect(DB_FILE)
    encrypted_df_readings = pd.read_sql_query('SELECT Timestamp, Data, Capsule '
                                              'FROM {} '
                                              'WHERE Timestamp > "{}" '
                                              'ORDER BY Timestamp;'
                                              .format(DB_NAME, last_timestamp), db_conn)

    for index, row in encrypted_df_readings.iterrows():
        capsule = pre.Capsule.from_bytes(bytes.fromhex(row['Capsule']), params=config.default_params())
        data_ciphertext = bytes.fromhex(row['Data'])

        alicia_pubkeys = demo_keys.get_alicia_pubkeys()
        bob_pubkeys = demo_keys.get_recipient_pubkeys()
        bob_privkeys = demo_keys.get_recipient_privkeys()
        nucypher_helper.reencrypt_data(alicia_pubkeys['enc'],
                                       bob_pubkeys['enc'],
                                       alicia_pubkeys['sig'],
                                       capsule)
        data_bytes = pre.decrypt(ciphertext=data_ciphertext,
                                 capsule=capsule,
                                 decrypting_key=bob_privkeys['enc'])

        readings = json.loads(data_bytes)
        readings['timestamp'] = row['Timestamp']
        df = df.append(readings, ignore_index=True)

    # only cache last 30 readings
    rows_to_remove = len(df) - 30
    if rows_to_remove > 0:
        df = df.iloc[rows_to_remove:]

    return df.to_json()


@app.callback(
    Output('pub-key', 'children'),
    events=[Event('gen-key-button', 'click')]
)
def gen_pubkey():
    bob_pubkeys = demo_keys.get_recipient_pubkeys()
    return bob_pubkeys['enc'].to_bytes().hex()


@app.callback(
    Output('measurements', 'children'),
    [Input('latest-decrypted-measurements', 'children')]
)
def update_graph(df_json_latest_measurements):
    graphs = []

    if df_json_latest_measurements is None:
        return graphs

    df = pd.read_json(df_json_latest_measurements, convert_dates=False)
    if len(df) == 0:
        return graphs

    # sort readings and order by timestamp
    df = df.sort_values(by='timestamp')

    # create joint graph for rpm and speed
    graphs.append(html.Div(get_rpm_speed_graph(df), className='four columns'))

    # add other graphs
    for key in PROPERTIES.keys():
        if key in ['rpm', 'speed']:
            # already added
            continue

        data = go.Scatter(
            y=df[key],
            fill='tozeroy',
            line=dict(
                color='#1E65F3',
            ),
            fillcolor='#9DC3E6'
        )

        graph_layout = go.Layout(
            title='{}'.format(PROPERTIES[key]),
            xaxis=dict(
                title='Time Elapsed (sec)',
                range=[0, 30],
                showgrid=False,
                showline=True,
                zeroline=False,
                fixedrange=True,
                tickvals=[0, 10, 20, 30],
                ticktext=['30', '20', '10', '0']
            ),
            yaxis=dict(
                title='{}'.format(PROPERTIES[key]),
                range=[min(df[key]), max(df[key])],
                zeroline=False,
                fixedrange=False),
            margin=Margin(
                t=45,
                l=50,
                r=1,
                b=1),
        )

        graphs.append(html.Div(dcc.Graph(id=key, figure={'data': [data], 'layout': graph_layout}),
                               className='four columns'))

    return graphs


def get_rpm_speed_graph(df: pd.DataFrame) -> dcc.Graph:
    rpm_data = go.Scatter(
        y=df['rpm'],
        name='RPM'
    )
    speed_data = go.Scatter(
        y=df['speed'],
        name='Speed',
        yaxis='y2'
    )
    data = [rpm_data, speed_data]

    graph_layout = go.Layout(
        title='RPM and Speed',
        xaxis=dict(
            title='Time Elapsed (sec)',
            range=[0, 30],
            fixedrange=True,
            tickvals=[0, 10, 20, 30],
            ticktext=['30', '20', '10', '0']
        ),
        yaxis=dict(
            title='{}'.format(PROPERTIES['rpm']),
            zeroline=False,
        ),
        yaxis2=dict(
            title='{}'.format(PROPERTIES['speed']),
            overlaying='y',
            side='right',
            zeroline=False,
        )
    )
    fig = go.Figure(data=data, layout=graph_layout)

    return dcc.Graph(id='rpm_speed', figure=fig)
