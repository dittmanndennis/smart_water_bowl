import asyncio
import time

import paho.mqtt.client as mqtt_client

from constants import MQTT_BROKER

client = mqtt_client.Client()
client.connect(MQTT_BROKER['HOST'], MQTT_BROKER['TCP_PORT'], 60)

async def main():
    #sampling_rate, calibration, alarm_level, alarm_counter
    client.publish(MQTT_BROKER['TOPIC'], payload=b"60, 300, 200, 10")

    print("published")

    time.sleep(20)

if __name__ == "__main__":
    while True:
        asyncio.run(main())
