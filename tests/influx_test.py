from influxdb_client import InfluxDBClient
import asyncio
import time

from constants import INFLUXDB

async def main():
    org = INFLUXDB['ORG']
    client = InfluxDBClient(url=INFLUXDB['URL'], token=INFLUXDB['TOKEN'], org=org)
    write_api = client.write_api()
    query_api = client.query_api()

    write_api.write(INFLUXDB['BUCKET'], org, [{"measurement": "tempValue", "tags": {"user": "Dennis"}, "fields": {"value": str(69420)}}, {"measurement": "humValue", "tags": {"user": "Dennis"}, "fields": {"value": str(69420)}}, {"measurement": "gasValue", "tags": {"user": "Dennis"}, "fields": {"value": str(69420)}}])
    
    query = ' from(bucket:"Exam")\
            |> range(start: -10m)\
            |> filter(fn: (r) => r._measurement == "tempValue")\
            |> filter(fn: (r) => r.user == "Dennis")\
            |> filter(fn: (r) => r._field == "value" )'
    result = query_api.query(org=org, query=query)

    results = []
    for table in result:
        for record in table.records:
            results.append((record.get_value(), record.get_field()))

    print(results)

    time.sleep(20)

if __name__ == "__main__":
    while True:
        asyncio.run(main())

