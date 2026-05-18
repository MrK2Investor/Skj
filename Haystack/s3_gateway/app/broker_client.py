from __future__ import annotations
from collections.abc import AsyncIterator
from typing import Any
import msgpack
import websockets

class BrokerClient:
    def __init__(self, url: str):
        self.url = url
        self.ws = None

    async def connect(self):
        self.ws = await websockets.connect(self.url, max_size=None)

    async def close(self):
        if self.ws is not None:
            await self.ws.close()

    async def subscribe(self, topic: str):
        await self.ws.send(msgpack.packb({"action": "subscribe", "topic": topic}, use_bin_type=True))
        await self.ws.recv()

    async def publish(self, topic: str, payload: dict[str, Any]):
        await self.ws.send(msgpack.packb({"action": "publish", "topic": topic, "payload": payload}, use_bin_type=True))

    async def listen(self) -> AsyncIterator[dict[str, Any]]:
        while True:
            raw = await self.ws.recv()
            yield msgpack.unpackb(raw, raw=False)
