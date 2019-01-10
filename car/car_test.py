import paho.mqtt.client as mqtt
import msgpack

CAR_DATA_FILENAME = 'car_data_bob.msgpack'

data_source_public_key = ""

# The callback for when the client receives a CONNACK response from the server.
#def on_connect(client, userdata, rc):
#    print("Connected with result code "+str(rc))
    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
#    client.subscribe("/Alicia_Car_Data")

# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
    #print(msg.topic+" "+str(msg.payload))
    if msg.topic == "/Alicia_Car_Data":
        print(msg.payload)
        kits.append(msg.payload)
    if msg.topic == "/Alicia_Car_Data/data_source_public_key":
        print("Data Source Public Key "+ str(msg.payload))
        data_source_public_key = msg.payload
    if msg.topic == "/Alicia_Car_Data/end":
        data = {
            'data_source': 'something',
            'kits': kits,
        }
        with open(CAR_DATA_FILENAME, "wb") as file:
            msgpack.dump(data, file, use_bin_type=True)

        

        

kits = list()
client = mqtt.Client()
#client.on_connect = on_connect
client.on_message = on_message

client.username_pw_set('e4d2dcb6', '4ce4f71d6411e9d0')

client.connect("broker.shiftr.io", 1883, 60)

client.subscribe("/Alicia_Car_Data")
client.subscribe("/Alicia_Car_Data/public_key")
client.subscribe("/Alicia_Car_Data/end")
client.subscribe("/Alicia_Car_Data/data_source_public_key")
# Blocking call that processes network traffic, dispatches callbacks and
# handles reconnecting.
# Other loop*() functions are available that give a threaded interface and a
# manual interface.
client.loop_forever()
