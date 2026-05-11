from __future__ import annotations

import json
from typing import Any

import msgpack
import websockets
from fastapi import APIRouter, Header
from pydantic import BaseModel, Field


router = APIRouter(prefix="/buckets", tags=["Image processing"])


BROKER_URL = "ws://localhost:8000/broker?fmt=json"
IMAGE_JOBS_TOPIC = "image.jobs"


class ImageProcessRequest(BaseModel):
    operation: str = Field(..., examples=["grayscale"])
    params: dict[str, Any] = Field(default_factory=dict)


def encode_json(data: dict[str, Any]) -> str:
    return json.dumps(data)


@router.post("/{bucket_id}/objects/{file_id}/process")
async def process_object(
    bucket_id: int,
    file_id: str,
    request: ImageProcessRequest,
    x_user_id: str = Header(...),
):
    job_payload = {
        "bucket_id": bucket_id,
        "file_id": file_id,
        "user_id": x_user_id,
        "operation": request.operation,
        "params": request.params,
    }

    async with websockets.connect(BROKER_URL, max_size=None) as websocket:
        await websocket.send(
            encode_json(
                {
                    "action": "publish",
                    "topic": IMAGE_JOBS_TOPIC,
                    "payload": job_payload,
                }
            )
        )

    return {
        "status": "processing_started",
        "topic": IMAGE_JOBS_TOPIC,
        "file_id": file_id,
        "operation": request.operation,
    }
