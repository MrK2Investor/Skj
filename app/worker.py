from __future__ import annotations

import argparse
import asyncio
import json
from typing import Any

import httpx
import msgpack
import websockets

from image_processor import ImageProcessingError, process_image_bytes


IMAGE_JOBS_TOPIC = "image.jobs"
IMAGE_DONE_TOPIC = "image.done"


def encode(data: dict[str, Any], fmt: str) -> str | bytes:
    if fmt == "msgpack":
        return msgpack.packb(data, use_bin_type=True)
    return json.dumps(data)


def decode(data: str | bytes, fmt: str) -> dict[str, Any]:
    if fmt == "msgpack":
        if isinstance(data, str):
            data = data.encode("utf-8")
        return msgpack.unpackb(data, raw=False)

    if isinstance(data, bytes):
        data = data.decode("utf-8")
    return json.loads(data)


async def publish_done(
    websocket,
    fmt: str,
    payload: dict[str, Any],
) -> None:
    await websocket.send(
        encode(
            {
                "action": "publish",
                "topic": IMAGE_DONE_TOPIC,
                "payload": payload,
            },
            fmt,
        )
    )


async def ack_job(websocket, fmt: str, message_id: int | None) -> None:
    if message_id is None:
        return

    await websocket.send(
        encode(
            {
                "action": "ack",
                "message_id": message_id,
            },
            fmt,
        )
    )


async def process_job(
    job: dict[str, Any],
    gateway_url: str,
    websocket,
    fmt: str,
) -> None:
    message_id = job.get("message_id")
    payload = job.get("payload") or {}

    file_id = payload.get("file_id")
    bucket_id = payload.get("bucket_id")
    user_id = payload.get("user_id")
    operation = payload.get("operation")
    params = payload.get("params") or {}

    try:
        if not file_id or not bucket_id or not user_id or not operation:
            raise ImageProcessingError(
                "Job must contain file_id, bucket_id, user_id and operation"
            )

        async with httpx.AsyncClient(timeout=60.0) as client:
            download_response = await client.get(
                f"{gateway_url}/files/{file_id}",
                headers={
                    "x-user-id": str(user_id),
                    "x-internal-source": "true",
                },
            )
            download_response.raise_for_status()

            processed_bytes = process_image_bytes(
                download_response.content,
                operation=operation,
                params=params,
            )

            output_filename = f"{file_id}_{operation}.png"

            upload_response = await client.post(
                f"{gateway_url}/files/upload",
                headers={
                    "x-user-id": str(user_id),
                    "bucket-id": str(bucket_id),
                    "x-internal-source": "true",
                },
                files={
                    "file": (
                        output_filename,
                        processed_bytes,
                        "image/png",
                    )
                },
            )
            upload_response.raise_for_status()

        await publish_done(
            websocket,
            fmt,
            {
                "status": "done",
                "source_file_id": file_id,
                "operation": operation,
                "result": upload_response.json(),
            },
        )

    except Exception as exc:
        await publish_done(
            websocket,
            fmt,
            {
                "status": "error",
                "source_file_id": file_id,
                "operation": operation,
                "error": str(exc),
            },
        )

    finally:
        # ACK posíláme i při chybě, protože job byl zpracován.
        # Chyba je oznámena do image.done.
        await ack_job(websocket, fmt, message_id)


async def run_worker(
    broker_url: str,
    gateway_url: str,
    fmt: str = "json",
) -> None:
    while True:
        try:
            async with websockets.connect(broker_url, max_size=None) as websocket:
                await websocket.send(
                    encode(
                        {
                            "action": "subscribe",
                            "topic": IMAGE_JOBS_TOPIC,
                        },
                        fmt,
                    )
                )

                print(f"Worker listening on topic {IMAGE_JOBS_TOPIC}")

                while True:
                    raw = await websocket.recv()
                    message = decode(raw, fmt)

                    if message.get("action") != "deliver":
                        continue

                    await process_job(
                        job=message,
                        gateway_url=gateway_url,
                        websocket=websocket,
                        fmt=fmt,
                    )

        except Exception as exc:
            print(f"Worker connection error: {exc}. Reconnecting in 2 seconds...")
            await asyncio.sleep(2)


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--broker-url",
        default="ws://localhost:8000/broker?fmt=json",
    )
    parser.add_argument(
        "--gateway-url",
        default="http://localhost:8000",
    )
    parser.add_argument(
        "--format",
        choices=["json", "msgpack"],
        default="json",
    )

    args = parser.parse_args()

    await run_worker(
        broker_url=args.broker_url,
        gateway_url=args.gateway_url,
        fmt=args.format,
    )


if __name__ == "__main__":
    asyncio.run(main())
