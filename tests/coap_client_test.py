import logging
import asyncio

from aiocoap import *
from aiocoap.numbers.codes import POST

logging.basicConfig(level=logging.INFO)

async def main():
    """Perform a single PUT request to localhost on the default port, URI
    "/other/block". The request is sent 2 seconds after initialization.

    The payload is bigger than 1kB, and thus sent as several blocks."""

    context = await Context.create_client_context()

    await asyncio.sleep(2)

    #sampling_rate, calibration, alarm_level, alarm_counter
    payload = "15, 1, 300, 4"
    request = Message(code=POST, payload=payload.encode(), uri="coap://192.168.2.177:5683/config")

    #payload = str(True) + ", " + str(69420) + ", " + str(69420) + ", " + str(69420) + ", " + str(69420)
    #request = Message(code=POST, payload=payload.encode(), uri="coap://127.0.0.1:5683/data")

    response = await context.request(request).response

    print('Result: %s\n%r'%(response.code, response.payload))

if __name__ == "__main__":
    asyncio.run(main())
