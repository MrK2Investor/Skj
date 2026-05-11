import asyncio
from typing import Dict, Set

from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, topic: str) -> None:
        if topic not in self.active_connections:
            self.active_connections[topic] = set()

        self.active_connections[topic].add(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        empty_topics = []

        for topic, clients in self.active_connections.items():
            clients.discard(websocket)

            if not clients:
                empty_topics.append(topic)

        for topic in empty_topics:
            del self.active_connections[topic]

    async def broadcast(self, topic: str, data: str | bytes) -> None:
        clients = list(self.active_connections.get(topic, set()))

        if not clients:
            return

        tasks = []

        for websocket in clients:
            if isinstance(data, bytes):
                tasks.append(websocket.send_bytes(data))
            else:
                tasks.append(websocket.send_text(data))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for websocket, result in zip(clients, results):
            if isinstance(result, Exception):
                self.disconnect(websocket)