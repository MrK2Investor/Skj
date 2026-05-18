from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import DefaultDict, Set

import msgpack
from fastapi import FastAPI, WebSocket, WebSocketDisconnect

app = FastAPI(title="Appify Message Broker")

class TopicManager:
    def __init__(self) -> None:
        self.topics: DefaultDict[str, Set[WebSocket]] = defaultdict(set)
        self.lock = asyncio.Lock()

    async def subscribe(self, topic: str, websocket: WebSocket) -> None:
        async with self.lock:
            self.topics[topic].add(websocket)

    async def unsubscribe_all(self, websocket: WebSocket) -> None:
        async with self.lock:
            for subscribers in self.topics.values():
                subscribers.discard(websocket)

    async def publish(self, topic: str, payload: bytes) -> None:
        async with self.lock:
            subscribers = list(self.topics.get(topic, set()))
        dead: list[WebSocket] = []
        for ws in subscribers:
            try:
                await ws.send_bytes(payload)
            except Exception:
                dead.append(ws)
        if dead:
            async with self.lock:
                for ws in dead:
                    for subscribers in self.topics.values():
                        subscribers.discard(ws)

manager = TopicManager()

@app.get("/health")
def health():
    return {"status": "ok"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            raw = await websocket.receive_bytes()
            message = msgpack.unpackb(raw, raw=False)
            action = message.get("action")
            topic = message.get("topic")

            if action == "subscribe":
                await manager.subscribe(topic, websocket)
                await websocket.send_bytes(msgpack.packb({"type": "subscribed", "topic": topic}, use_bin_type=True))

            elif action == "publish":
                payload = msgpack.packb({"topic": topic, "payload": message.get("payload")}, use_bin_type=True)
                await manager.publish(topic, payload)

            else:
                await websocket.send_bytes(msgpack.packb({"type": "error", "detail": "Unknown action"}, use_bin_type=True))
    except WebSocketDisconnect:
        await manager.unsubscribe_all(websocket)
    except Exception:
        await manager.unsubscribe_all(websocket)
