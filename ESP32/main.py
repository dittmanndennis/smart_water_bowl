from machine import Pin
from time import sleep, time
from hx711_gpio import HX711
import dht


# SENSORS

sensor = dht.DHT11(Pin(14))
weight_OUT = Pin(26, Pin.IN, pull=Pin.PULL_DOWN)
weight_SCK = Pin(27, Pin.OUT)
weight_sensor = HX711(weight_SCK, weight_OUT)


# Calibration

print("Taring...")
sleep(2)
weight_sensor.tare(100)
print("Tare done.")
print("Place a known weight on the scale.")
sleep(10)
print("reading...")
value = 0
for i in range(100):
    value += weight_sensor.get_value()
value = value/100
print("Weight: ", value)
# 1580g = weight of 1.5l water bottle, ADJUST to YOUR measurement unit!!!
weight_sensor.set_scale(value/1580)


# Logic

while True:
    try:
        mqtt_client.check_msg()
        if (time() - _last_sample) >= _sampling_rate:
            try:
                weight_sensor.power_up()
                weight = weight_sensor.get_units()
                weight_sensor.power_down()
                
                if weight <= _alarm_level:
                    _alarms += 1
                else:
                    _alarms = 0
                
                sensor.measure()
                temp = sensor.temperature()
                hum = sensor.humidity()
                
                rssi = wlan.status('rssi')
                
                latency = post_data(coap_client, str(_alarms>=_alarm_counter), str(weight), str(temp), str(hum), str(rssi))
                if len(_coap_latency) == 100:
                    _coap_latency.pop(0)
                _coap_latency.append(latency)
                print("Coap lateny: ",sum(_coap_latency)/len(_coap_latency))
                print(_coap_latency)
                
                _last_sample = time()
            except OSError as e:
                print("Failed to read sensor.")
    except OSError as e:
        restart_and_reconnect()
