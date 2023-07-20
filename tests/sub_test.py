import paho.mqtt.client as mqtt_client

from constants import MQTT_BROKER

# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, rc):
    print("Connected with result code "+str(rc))

    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    client.subscribe(MQTT_BROKER['TOPIC'])

# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
    #sampling_rate, calibration, alarm_level, alarm_counter
    reading = msg.payload.decode()
    sampling_rate, calibration, alarm_level, alarm_counter = reading.split(", ")
    print(reading)
    print(sampling_rate)
    print(calibration)
    print(alarm_level)
    print(alarm_counter)

client = mqtt_client.Client()
client.on_connect = on_connect
client.on_message = on_message
client.connect(MQTT_BROKER['HOST'], MQTT_BROKER['TCP_PORT'], 60)

# Blocking call that processes network traffic, dispatches callbacks and
# handles reconnecting.
# Other loop*() functions are available that give a threaded interface and a
# manual interface.
client.loop_forever()
