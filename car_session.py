import time
import json
import msgpack
import sqlite3
import pandas as pd
import paho.mqtt.client as mqtt

from nucypher.data_sources import DataSource

from umbral.keys import UmbralPublicKey

# Test public key
pub_key_bytes = b'\x03\x07a\xebt|&\x8d\xb6\xb7\xd5b\xf1\x8f\xe1,\xf9n1\xa7\xcf\xe0\xec\xff~E\xdd\x8c.\x8bB\xe4\xbd'

DB_FILE = './data/vehicle_sensors.db'
DB_NAME = 'VehicleData'

DATA_FILENAME = 'car_data.msgpack'
RECORDED_CAR_SESSION = "UMA-5_10_17-session.db"

MQTT_USERNAME = '10288942'
MQTT_PASSWD = '184def19b4bbb41a'
MQTT_HOST = "broker.shiftr.io"
MQTT_PORT = 1883

# Alicia defined a label to categorize all her heart-related data ❤️
# All DataSources that produce this type of data will use this label.
DEFAULT_LABEL = b"Alicia's car data"


def reproduce_stored_session(policy_pubkey_bytes: bytes,
                             label: bytes = DEFAULT_LABEL,
                             save_as_file: bool = False,
                             send_by_mqtt: bool = False,
                             store_in_db: bool = False):

    policy_pubkey = UmbralPublicKey.from_bytes(policy_pubkey_bytes)

    data_source = DataSource(policy_pubkey_enc=policy_pubkey, label=label)

    data_source_public_key = bytes(data_source.stamp)

    # path of session database file
    sessionPath = RECORDED_CAR_SESSION

    if send_by_mqtt:
        # Connect to MQTT platform
        client = mqtt.Client()
        client.username_pw_set(MQTT_USERNAME, MQTT_PASSWD)
        client.connect(MQTT_HOST, MQTT_PORT, 60)

        # Communication is starting: send public key
        client.publish("/Alicia_Car_Data/public_key", pub_key_bytes)
        client.publish("/Alicia_Car_Data/data_source_public_key", data_source_public_key)


    # Message kits list
    kits = list()
    try:
        # Connection to saved session database
        db = sqlite3.connect(sessionPath)
        tripCurs = db.cursor()
        gpsCurs = db.cursor()
        obdCurs = db.cursor()
        beacons_dataCurs = db.cursor()

        # Data Base cursor for beacons data table
        beacons_dataCurs.execute("SELECT * FROM beacons_data")
        # take the first beacon data row from table
        beacons_dataRow = beacons_dataCurs.fetchone()

        # everytime that engine stop and start during session saving, new trip is created
        for trip in tripCurs.execute("SELECT * FROM trip"):
            start = trip[1]
            end = trip[2]

            nextTime = None

            for gpsRow in gpsCurs.execute("SELECT * FROM gps WHERE time>=(?) AND time<(?)", (start, end)):
                # if this is not the first iteration...
                if nextTime != None:
                    currentTime = nextTime
                    nextTime = gpsRow[6]

                    # time difference between two samples
                    diff = nextTime - currentTime

                    # sleep the thread: simulating gps signal delay
                    #time.sleep(0.01)

                    # take the same sample from obd table
                    obdCurs.execute("SELECT * FROM obd WHERE time=(?)", (currentTime,))
                    obdRow = obdCurs.fetchone()

                    # obtained information about OBDII & GPS from sessions database
                    temp = int(obdRow[0])
                    rpm = int(obdRow[1])
                    vss = int(obdRow[2])
                    maf = obdRow[3]
                    throttlepos = obdRow[4]
                    lat = gpsRow[0]
                    lon = gpsRow[1]
                    alt = gpsRow[2]
                    gpsSpeed = gpsRow[3]
                    course = int(gpsRow[4])
                    gpsTime = int(gpsRow[5])

                    # structure for generating msgpack
                    car_data = {"carInfo": {"engineOn": True, "temp": temp, "rpm": rpm, "vss": vss, "maf": maf,
                                            "throttlepos": throttlepos, "lat": lat, "lon": lon, "alt": alt,
                                            "gpsSpeed": gpsSpeed, "course": course, "gpsTime": gpsTime}}

                    plaintext = msgpack.dumps(car_data, use_bin_type=True)
                    message_kit, _signature = data_source.encrypt_message(plaintext)

                    kit_bytes = message_kit.to_bytes()
                    kits.append(kit_bytes)

                    if send_by_mqtt:
                        client.publish("/Alicia_Car_Data", kit_bytes)

                    if store_in_db:
                        df = pd.DataFrame.from_dict({
                            'Timestamp': [time.time()],
                            'EncryptedData': [kit_bytes.hex()],
                        })

                        # add new vehicle data
                        db_conn = sqlite3.connect(DB_FILE)
                        df.to_sql(name=DB_NAME, con=db_conn, index=False, if_exists='append')

                        print('Added vehicle sensor readings to db: ', car_data)

                else:
                    nextTime = gpsRow[6]

    finally:
        if db:
            db.close()

        if send_by_mqtt:
            client.publish("/Alicia_Car_Data/end", "end")

        data = {
            'data_source': data_source_public_key,
            'kits': kits,
        }

        if save_as_file:
            with open(DATA_FILENAME, "wb") as file:
                msgpack.dump(data, file, use_bin_type=True)

        data_json = json.dumps(car_data)

        return data_json


# Only for developing and testing purposes.
if __name__ == "__main__":
    reproduce_stored_session(pub_key_bytes, save_as_file=True, send_by_mqtt=True)
