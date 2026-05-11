import asyncio
import json
import time

import msgpack
import websockets


URL_JSON = "ws://localhost:8000/broker?fmt=json"
URL_MSGPACK = "ws://localhost:8000/broker?fmt=msgpack"

TOPIC = "benchmark"
PUBLISHERS = 5
SUBSCRIBERS = 5
MESSAGES_PER_PUBLISHER = 100


def encode(data: dict, fmt: str):
    if fmt == "msgpack":
        return msgpack.packb(data, use_bin_type=True)

    return json.dumps(data)


def decode(data, fmt: str):
    if fmt == "msgpack":
        return msgpack.unpackb(data, raw=False)

    return json.loads(data)


async def subscriber(fmt: str, expected: int):
    url = URL_MSGPACK if fmt == "msgpack" else URL_JSON

    received = 0

    async with websockets.connect(url, max_size=None) as websocket:
        await websocket.send(
            encode(
                {
                    "action": "subscribe",
                    "topic": TOPIC,
                },
                fmt,
            )
        )

        while received < expected:
            raw = await websocket.recv()
            message = decode(raw, fmt)

            received += 1

            await websocket.send(
                encode(
                    {
                        "action": "ack",
                        "message_id": message["message_id"],
                    },
                    fmt,
                )
            )

    return received


async def publisher(fmt: str, publisher_id: int):
    url = URL_MSGPACK if fmt == "msgpack" else URL_JSON

    async with websockets.connect(url, max_size=None) as websocket:
        for i in range(MESSAGES_PER_PUBLISHER):
            await websocket.send(
                encode(
                    {
                        "action": "publish",
                        "topic": TOPIC,
                        "payload": {
                            "publisher": publisher_id,
                            "index": i,
                            "value": "hello",
                        },
                    },
                    fmt,
                )
            )


async def run_benchmark(fmt: str):
    total_published = PUBLISHERS * MESSAGES_PER_PUBLISHER
    total_expected_per_subscriber = total_published

    subscriber_tasks = [
        asyncio.create_task(subscriber(fmt, total_expected_per_subscriber))
        for _ in range(SUBSCRIBERS)
    ]

    await asyncio.sleep(1)

    start = time.perf_counter()

    publisher_tasks = [
        asyncio.create_task(publisher(fmt, i))
        for i in range(PUBLISHERS)
    ]

    await asyncio.gather(*publisher_tasks)
    await asyncio.gather(*subscriber_tasks)

    elapsed = time.perf_counter() - start

    total_delivered = total_published * SUBSCRIBERS
    throughput = total_delivered / elapsed

    print(f"Format: {fmt}")
    print(f"Published messages: {total_published}")
    print(f"Delivered messages: {total_delivered}")
    print(f"Time: {elapsed:.2f} s")
    print(f"Throughput: {throughput:.2f} msg/s")


async def main():
    await run_benchmark("json")
    await run_benchmark("msgpack")


if __name__ == "__main__":
    asyncio.run(main())