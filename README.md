# Smart Water Bowl

This repository consists of the software to create a smart water bowl that alerts you on the occurence of low water levels. The software provided for this is our proxy module and ESP32 sketch. Furtheremore, this repository inhabits a prediction module that can forecast future water levels based on weight, temperature, and humidity.

# ESP32

The ESP32 sketch works in the following way:
First, a wifi connection is established. Then, the controller subscribes to the specified MQTT broker and topic. Next, the load sensor is calibrated with a known weight. Finally, the system settles into its standard operation state where it checks for new configurations in the MQTT broker and sends sensor readings according to the sampling rate to the specified CoAP client.

## Setup

The Micropython files in the ESP32 folder should be copied entirely onto your ESP32 unit. Be aware that you need to alter the global variables in the `boot.py` file according to your environment. Finally, RST your ESP32 unit.

# Proxy

The proxy module runs the CoAP server that the ESP32 sketch connects to. This server has two endpoints. One that forwards the sensor readings to your InfluxDB instance and a second one that initiates configuration changes. Furthermore, the proxy module also manages a Telegram bot. This  bot sends out alarms to subscribed users, if the water level gets to low. Additionally, this bot can receive and forward configuration changes to the ESP32 controller.

## Setup

To setup the proxy module, fill the `constants.py` with your credentials. You might need to create your own InfluxDB instance for that. Install the `requirements.txt` Finally, run the script.

## API

### `/config`

- forwards config change to ESP32 unit

POST (Bytes)

`sampling_rate, calibration, alarm_level, alarm_counter`

```
Number, Number, Number, Number
```

# Prediction

The prediction module has three pairs of functions. Each function pair either uses only the weight or the weight, temperature, and humidity for its forecast. The function pairs consist of: inserting forecast for the next 24 hours into your forecast bucket of your InfluxDB instance, predicting the amount of time left until the next alarm is raised, and the mean squared error of each forecast.

## Setup

To setup the prediction module, fill the `constants.py` with your credentials. You might need to create your own InfluxDB instance for that. Install the `requirements.txt` Finally, run the script.
