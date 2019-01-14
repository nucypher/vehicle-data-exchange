import random
import time
import signal
import msgpack
import sqlite3
import json
import paho.mqtt.client as mqtt
import paho.mqtt.subscribe as subscribe
import obd
import pandas as pd

from nucypher.data_sources import DataSource
from umbral import pre
from umbral.keys import UmbralPublicKey

# pub_key_bytes = b'\x03\x07a\xebt|&\x8d\xb6\xb7\xd5b\xf1\x8f\xe1,\xf9n1\xa7\xcf\xe0\xec\xff~E\xdd\x8c.\x8bB\xe4\xbd'

DATA_FILENAME = 'car_data.msgpack'
MQTT_USERNAME = '10288942'
MQTT_PASSWD = '184def19b4bbb41a'
MQTT_HOST = "broker.shiftr.io"
MQTT_PORT = 1883
MQTT_TOPIC = '/Alicia_Car_Data'

# Alicia defined a label to categorize all her data
# All DataSources that produce this type of data will use this label.
DEFAULT_LABEL = b"Alicia's car data"

class ServiceExit(Exception):
    # this is necessary for interrupt exception
    pass


def send_real_time_data ( policy_pubkey, label: bytes = DEFAULT_LABEL, save_as_file: bool = False, send_by_mqtt: bool = False, obd: bool = True, gps: bool = True, kms: bool = True ):

    # register the signal handlers for interrupting the execution
    signal.signal(signal.SIGTERM, service_shutdown)
    signal.signal(signal.SIGINT, service_shutdown)
    
    data_source = DataSource(policy_pubkey_enc=policy_pubkey, label=label)
    data_source_public_key = bytes(data_source.stamp)
    
    # Message kits list
    kits = list()
    
    if send_by_mqtt:

        # Connect to MQTT platform
        client = mqtt.Client()
        client.username_pw_set(MQTT_USERNAME, MQTT_PASSWD)
        client.connect(MQTT_HOST, MQTT_PORT, 60)

        # Communication is starting: send public key
        client.publish(MQTT_TOPIC+"/public_key", pub_key_bytes)
        client.publish(MQTT_TOPIC+"/data_source_public_key", data_source_public_key)


    try:
        if obd:
            connection = obd.OBD() # auto-connects to USB or RF port

        while (True):
            time.sleep(0.5)
            if obd:
                vss = connection.query(obd.commands.SPEED).value.magnitude # send the command, and parse the response
                rpm = connection.query(obd.commands.RPM).value.magnitude
                maf = connection.query(obd.commands.MAF).value.magnitude
                throttlepos = connection.query(obd.commands.THROTTLE_POS).value.magnitude
                temp = connection.query(obd.commands.COOLANT_TEMP).value.magnitude
            else:
                vss = 0
                rpm = 0
                maf = 0
                throttlepos = 0
                temp = 0

            if gps:
                print ("REAL TIME GPS DATA NOT YET IMPLEMENTED")
                lat = 4.0
                lon = 31.0
                alt = 100
                course = 34
                gpsTime = 110020
                gpsSpeed = 99
            else:
                lat = 4.0
                lon = 31.0
                alt = 100
                course = 34
                gpsTime = 110020
                gpsSpeed = 99

            car_data = {"carInfo": {"engineOn":True, "temp":temp, "rpm":rpm, "vss":vss, "maf":maf, "throttlepos":throttlepos, "lat":lat, "lon":lon, "alt":alt, "gpsSpeed":gpsSpeed, "course":course, "gpsTime":gpsTime} }

            print (car_data)

            timestamp = time.time()

            if kms:
                plaintext = msgpack.dumps(car_data, use_bin_type=True)
                message_kit, _signature = data_source.encrypt_message(plaintext)

                kit_bytes = message_kit.to_bytes()
                kits.append(kit_bytes)

                car_data_entry = {
                    'Timestamp': [timestamp],
                    'Data': [kit_bytes.hex()]
                }

            else:
                latest_readings = json.dumps(car_data)
                # policy_pubkey = UmbralPublicKey.from_bytes(policy_pubkey)
                ciphertext, capsule = pre.encrypt(policy_pubkey, latest_readings.encode('utf-8'))

                car_data_entry = {
                    'Timestamp': [timestamp],
                    'Data': [ciphertext.hex()],
                    'Capsule': [capsule.to_bytes().hex()]
                }

            if send_by_mqtt:
                client.publish(MQTT_TOPIC, json.dumps(car_data_entry))

    # if receive terminal signal
    except ServiceExit:
        print("Terminal Signal received")
        client.publish(MQTT_TOPIC+"/end", "end")

        data = {
            'data_source': data_source_public_key,
            'kits': kits,
        }
        print("Terminal Signal received")

        if save_as_file:
            with open(DATA_FILENAME, "wb") as file:
                msgpack.dump(data, file, use_bin_type=True)

        return data

# this is the interrupt handler. Used when the thread is finished (ctrl+c from keyboard)
def service_shutdown(signum, frame):
    raise ServiceExit

# Only for developing and testing purpouses. Comment if you call the functions from other script
if __name__ == "__main__":
    
    pub_key_bytes = bytes(subscribe.simple (MQTT_TOPIC+'/public_key', hostname=MQTT_HOST,auth={'username': MQTT_USERNAME, 'password': MQTT_PASSWD}).payload)

    print ('pub_key received')
    print (pub_key_bytes)

    pub_key = UmbralPublicKey.from_bytes(pub_key_bytes)

    send_real_time_data(pub_key, save_as_file = True, send_by_mqtt = True, obd = False, gps = False)