import logging
import asyncio

from constants import INFLUXDB, MQTT_BROKER, TELEGRAM_BOT

import aiocoap
import aiocoap.resource as resource
import paho.mqtt.client as mqtt_client
from influxdb_client import InfluxDBClient
from telebot.async_telebot import AsyncTeleBot


# logging setup

logging.basicConfig(level=logging.INFO)
logging.getLogger("coap-server").setLevel(logging.DEBUG)



# Telegram Bot setup

_alarmed = False
_bot_chats = set()
bot = AsyncTeleBot(TELEGRAM_BOT['TOKEN'])

async def alarm_chat(chat):
    await bot.send_message(chat, "The water level in your pets bowl is low!")

@bot.message_handler(commands=['start', 'help'])
async def send_welcome(message):
    await bot.reply_to(message, "Hi! I can alarm you when your pet's water bowl runs out of water. With me, you can also change the configuration of your pet's water bowl.\n\n/alarm - subscribes or unsubscribes you from alarms\n/config - lets you adjust the bowls configuration with the pattern: /config \{sampling_rate\}, \{calibration\}, \{alarm_level\}, \{alarm_counter\}")

@bot.message_handler(commands=['alarm'])
async def alarm(message):
    if message.chat.id in _bot_chats:
        _bot_chats.remove(message.chat.id)
        await bot.reply_to(message, "I unsubscribed you from alarms!")
    else:
        _bot_chats.add(message.chat.id)
        await bot.reply_to(message, "I subscribed you to alarms!")

@bot.message_handler(commands=['config'])
async def config(message):
    payload = message.text.split(" ", 1)[1].encode()
    print("Config POST payload: ", payload)

    #sampling_rate, calibration, alarm_level, alarm_counter
    client = mqtt_client.Client()
    client.connect(MQTT_BROKER['HOST'], MQTT_BROKER['TCP_PORT'], 60)
    client.publish(MQTT_BROKER['TOPIC'], payload=payload)

    await bot.reply_to(message, "I updated the bowls configuration!")



# CoAP setup

class DataResource(resource.Resource):
    async def render_post(self, request):
        global _alarmed
        payload = request.payload.decode()
        alarm, weight, temp, hum, rssi = payload.split(", ")
        print("Data POST payload: ", payload)

        record = {
                    "measurement": "water_bowl",
                    "tags": {
                        "alarm": alarm == "True"
                        },
                    "fields": {
                        "weight": float(weight),
                        "temperature": float(temp),
                        "humidity": float(hum),
                        "rssi": float(rssi)
                    }
                }
        write_api = InfluxDBClient(url=INFLUXDB['URL'], token=INFLUXDB['TOKEN'], org=INFLUXDB['ORG']).write_api()
        write_api.write(INFLUXDB['BUCKET'], INFLUXDB['ORG'], record)

        if alarm == "True" and not _alarmed:
             _alarmed = True
             map(alarm_chat, _bot_chats)
        elif alarm == "False":
             _alarmed = False

        return aiocoap.Message(code=aiocoap.CHANGED, payload=b"True")
    
class ConfigResource(resource.Resource):
    async def render_post(self, request):
        print("Config POST payload: ", request.payload.decode())

        #sampling_rate, calibration, alarm_level, alarm_counter
        client = mqtt_client.Client()
        client.connect(MQTT_BROKER['HOST'], MQTT_BROKER['TCP_PORT'], 60)
        client.publish(MQTT_BROKER['TOPIC'], payload=request.payload)

        return aiocoap.Message(code=aiocoap.CHANGED, payload=b"True")

class WhoAmI(resource.Resource):
    async def render_get(self, request):
        text = ["Used protocol: %s." % request.remote.scheme]

        text.append("Request came from %s." % request.remote.hostinfo)
        text.append("The server address used %s." % request.remote.hostinfo_local)

        claims = list(request.remote.authenticated_claims)
        if claims:
            text.append("Authenticated claims of the client: %s." % ", ".join(repr(c) for c in claims))
        else:
            text.append("No claims authenticated.")

        return aiocoap.Message(content_format=0,
                payload="\n".join(text).encode('utf8'))

async def coap():
    # Resource tree creation
    root = resource.Site()
    print(root)

    root.add_resource(['.well-known', 'core'],
            resource.WKCResource(root.get_resources_as_linkheader))
    root.add_resource(['whoami'], WhoAmI())
    root.add_resource(['data'], DataResource())
    root.add_resource(['config'], ConfigResource())

    # bind to machine network address (MacOs: ifconfig - status: active)
    await aiocoap.Context.create_server_context(bind=('192.168.2.177',5683), site=root)

    # Run forever
    await asyncio.get_running_loop().create_future()



async def main():
    coap_task = asyncio.create_task(coap())
    bot_task = asyncio.create_task(bot.polling())
    await asyncio.gather(coap_task, bot_task)

if __name__ == "__main__":
    asyncio.run(main())

