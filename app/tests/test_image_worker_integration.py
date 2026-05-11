import asyncio
import json

import pytest
import websockets


BROKER_URL = "ws://localhost:8000/broker?fmt=json"
JOBS_TOPIC = "image.jobs"
DONE_TOPIC = "image.done"


def encode(data: dict) -> str:
    return json.dumps(data)


def decode(data: str | bytes) -> dict:
    if isinstance(data, bytes):
        data = data.decode("utf-8")
    return json.loads(data)


@pytest.mark.asyncio
async def test_worker_processes_10_jobs_through_broker():
    """
    Tento test počítá s tím, že běží:
    1) FastAPI broker na localhost:8000
    2) worker.py připojený k brokeru
    3) S3 gateway s testovacími obrázky

    Pokud nechceš spouštět celý stack, nech tento test jako integrační
    a spouštěj ho ručně.
    """

    done_messages = []

    async with websockets.connect(BROKER_URL, max_size=None) as done_subscriber:
        await done_subscriber.send(
            encode(
                {
                    "action": "subscribe",
                    "topic": DONE_TOPIC,
                }
            )
        )

        async with websockets.connect(BROKER_URL, max_size=None) as publisher:
            for i in range(10):
                await publisher.send(
                    encode(
                        {
                            "action": "publish",
                            "topic": JOBS_TOPIC,
                            "payload": {
                                "bucket_id": 1,
                                "file_id": "test-image-id",
                                "user_id": "test-user",
                                "operation": "grayscale",
                                "params": {},
                                "job_index": i,
                            },
                        }
                    )
                )

        while len(done_messages) < 10:
            raw = await asyncio.wait_for(done_subscriber.recv(), timeout=30)
            message = decode(raw)

            assert message["action"] == "deliver"
            assert message["topic"] == DONE_TOPIC

            done_messages.append(message)

            await done_subscriber.send(
                encode(
                    {
                        "action": "ack",
                        "message_id": message["message_id"],
                    }
                )
            )

    assert len(done_messages) == 10
