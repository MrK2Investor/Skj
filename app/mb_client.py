import argparse
import asyncio
import json

import msgpack
import websockets


def encode(data: dict, fmt: str):
    if fmt == "msgpack":
        return msgpack.packb(data, use_bin_type=True)

    return json.dumps(data)


def decode(data, fmt: str):
    if fmt == "msgpack":
        return msgpack.unpackb(data, raw=False)

    return json.loads(data)


async def publisher(uri: str, topic: str, fmt: str):
    async with websockets.connect(uri) as websocket:
        while True:
            text = input("Message: ")

            message = {
                "action": "publish",
                "topic": topic,
                "payload": {
                    "text": text,
                },
            }

            await websocket.send(encode(message, fmt))


async def subscriber(uri: str, topic: str, fmt: str):
    async with websockets.connect(uri) as websocket:
        subscribe = {
            "action": "subscribe",
            "topic": topic,
        }

        await websocket.send(encode(subscribe, fmt))

        while True:
            raw = await websocket.recv()
            message = decode(raw, fmt)

            print("Received:", message)

            ack = {
                "action": "ack",
                "message_id": message["message_id"],
            }

            await websocket.send(encode(ack, fmt))


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["publisher", "subscriber"], required=True)
    parser.add_argument("--topic", required=True)
    parser.add_argument("--format", choices=["json", "msgpack"], default="json")
    parser.add_argument("--url", default=None)

    args = parser.parse_args()

    url = args.url or f"ws://localhost:8000/broker?fmt={args.format}"

    if args.mode == "publisher":
        await publisher(url, args.topic, args.format)
    else:
        await subscriber(url, args.topic, args.format)


if __name__ == "__main__":
    asyncio.run(main())