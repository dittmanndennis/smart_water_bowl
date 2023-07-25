# Smart Water Bowl

This consists of the software to create a smart water bowl that alerts you on the occurence of low water levels. The software provided for this is our proxy module and ESP32 sketch. Furtheremore, this repository inhabits a prediction module that can forecast future water levels based on weight, temperature, and humidity.

# ESP32

The Micropython files in the ESP32 folder should be copied entirely onto your ESP32 unit. Be aware that you need to alter the global variables in the boot.py file according to your environment.

The ESP32 sketch works in the following way:
First, a wifi connection is established. Then, the controller subscribes to the specified MQTT broker and topic. Next, the load sensor is calibrated with a known weight. Finally, the system settles into its standard operation state where it checks for new configurations in the MQTT broker and sends sensor readings according to the sampling rate to the specified CoAP client.

# Proxy

…

# Prediction

…
