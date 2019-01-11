import paho.mqtt.client as mqtt
import msgpack

CAR_DATA_FILENAME = 'car_data_bob.msgpack'


data = {
            'data_source': None,
            'kits': list(),
        }

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
        #print(msg.payload)
        kits = data['kits']
        kits.append(bytes(msg.payload))
    if msg.topic == "/Alicia_Car_Data/data_source_public_key":
        
        data_source_public_key = bytes(msg.payload)
        print("Data Source Public Key ")
        print(data_source_public_key)
        data['data_source'] = data_source_public_key
    if msg.topic == "/Alicia_Car_Data/end":          
        with open(CAR_DATA_FILENAME, "wb") as file:
            msgpack.dump(data, file, use_bin_type=True)
        quit()

        

        

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
