# This file is executed on every boot (including wake-boot from deepsleep)
import esp
esp.osdebug(None)
import gc
gc.collect()

from time import ticks_ms, sleep
import ubinascii
import machine
import network

import microcoapy
from coap_macros import COAP_CONTENT_FORMAT
from umqttsimple import MQTTClient


# ADJUST according to YOUR peripherals
_MY_SSID = 'YOUR_SSID'
_MY_PASS = 'YOUR_SSIDs_PASSWORD'
_COAP_HOST = 'YOUR_HOST_MACHINE'
_COAP_PORT = '5683'
_COAP_POST_URL = '/data'
_MQTT_HOST = 'broker.hivemq.com'
_MQTT_PORT = 1883
_MQTT_TOPIC = b'YOUR_TOPIC'
_MQTT_CLIENT_ID = ubinascii.hexlify(machine.unique_id())

_sampling_rate = 20.0
_calibration = 0.0
_alarm_level = 200.0
_alarm_counter = 3.0

# 1580g = weight of 1.5l water bottle, ADJUST to YOUR measurement unit!!!
_known_weight = 1580
_last_sample = 0
_alarms = 0
_coap_latency = []



wlan = network.WLAN(network.STA_IF)
if not wlan.isconnected():
    print('connecting to network...')
    wlan.active(True)
    wlan.connect(_MY_SSID, _MY_PASS)
    while not wlan.isconnected():
        machine.idle()
print('network config:', wlan.ifconfig())



# COAP

def post_data(coap_client, alarm, weight, temp, hum, rssi):
    coap_client.start()

    # About to post message...
    msg = alarm + ", " + weight + ", " + temp + ", " + hum + ", " + rssi
    latency = ticks_ms()
    messageId = coap_client.post(_COAP_HOST, _COAP_PORT, _COAP_POST_URL, msg, None, COAP_CONTENT_FORMAT.COAP_TEXT_PLAIN)

    # wait for response to our request for 2 seconds
    if coap_client.poll(timeoutMs=1000, pollPeriodMs=100):
        latency = ticks_ms() - latency
    else:
        latency = ticks_ms() - latency
        print("No message received!")
        
    coap_client.stop()
    
    return latency

def receivedMessageCallback(packet, sender):
    print('Message received:', packet.toString(), ', from: ', sender)

coap_client = microcoapy.Coap()
coap_client.discardRetransmissions = True
coap_client.responseCallback = receivedMessageCallback


# MQTT

def sub_cb(topic, msg):
    global _sampling_rate, _calibration, _alarm_level, _alarm_counter
    
    _sampling_rate, _calibration, _alarm_level, _alarm_counter = map(float, msg.decode().split(", "))
    if weight_sensor.SCALE != _calibration and _calibration != 0:
        weight_sensor.set_scale(_calibration)
        
    print((topic, msg))

def connect_and_subscribe():
    global _MQTT_CLIENT_ID, _MQTT_HOST, _MQTT_TOPIC
    mqtt_client = MQTTClient(_MQTT_CLIENT_ID, _MQTT_HOST)
    mqtt_client.set_callback(sub_cb)
    mqtt_client.connect()
    mqtt_client.subscribe(_MQTT_TOPIC)
    print('Connected to %s MQTT broker, subscribed to %s topic' % (_MQTT_HOST, _MQTT_TOPIC))
    return mqtt_client

def restart_and_reconnect():
    print('Failed to connect to MQTT broker. Reconnecting...')
    sleep(10)
    machine.reset()

try:
    mqtt_client = connect_and_subscribe()
except OSError as e:
    restart_and_reconnect()
