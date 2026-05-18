from __future__ import annotations

import asyncio

import httpx
from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import Response

from .broker_client import BrokerClient
from .config import settings
from .storage import HaystackStorage

app = FastAPI(title="Appify Haystack Storage Node")
storage = HaystackStorage(settings.volume_dir, settings.max_volume_size)

async def storage_write_listener():
    while True:
        try:
            client = BrokerClient(settings.broker_url)
            await client.connect()
            await client.subscribe("storage.write")
            async for msg in client.listen():
                payload = msg.get("payload", {})
                object_id = payload.get("object_id")
                data = payload.get("data")
                if not object_id or data is None:
                    continue
                location = await storage.append(data)
                await client.publish("storage.ack", {"object_id": object_id, **location})
        except Exception:
            await asyncio.sleep(2)

@app.on_event("startup")
async def startup():
    asyncio.create_task(storage_write_listener())

@app.get("/health")
def health():
    return {"status": "ok", "active_volume": storage.volume_id}

@app.get("/volume/{volume_id}/{offset}/{size}")
def read_volume(volume_id: int, offset: int, size: int):
    try:
        data = storage.read(volume_id, offset, size)
        return Response(content=data, media_type="application/octet-stream")
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Volume not found")
    except ValueError as exc:
        raise HTTPException(status_code=416, detail=str(exc))

@app.post("/admin/compact/{volume_id}")
async def compact(volume_id: int, x_admin_token: str | None = Header(default=None)):
    if x_admin_token != settings.admin_token:
        raise HTTPException(status_code=401, detail="Invalid admin token")
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.get(f"{settings.gateway_url}/admin/volumes/{volume_id}/live-objects", headers={"x-admin-token": settings.admin_token})
        resp.raise_for_status()
        live_objects = resp.json()["objects"]

    updates = storage.compact_volume(volume_id, live_objects)

    async with httpx.AsyncClient(timeout=60) as client:
        for update in updates:
            resp = await client.post(f"{settings.gateway_url}/admin/objects/{update['object_id']}/location", json=update, headers={"x-admin-token": settings.admin_token})
            resp.raise_for_status()

    return {"volume_id": volume_id, "moved_objects": len(updates)}
