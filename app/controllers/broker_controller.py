from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from app.core.broker_serializer import BrokerSerializer
from app.core.broker_protocol import BrokerMessage, DeliverMessage
from app.core.connection_manager import ConnectionManager
from app.repositories.queued_message_repository import QueuedMessageRepository
from app.models.queued_message_model import QueuedMessageModel
from datetime import datetime

router = APIRouter()
manager = ConnectionManager()
repo = QueuedMessageRepository()


async def _send(websocket: WebSocket, fmt: str, data: dict):
    encoded = BrokerSerializer.encode(data, fmt)

    if isinstance(encoded, bytes):
        await websocket.send_bytes(encoded)
    else:
        await websocket.send_text(encoded)


async def _send_error(websocket: WebSocket, fmt: str, detail: str):
    await _send(websocket, fmt, {
        "action": "error",
        "detail": detail,
    })


@router.websocket("/broker")
async def broker_endpoint(websocket: WebSocket, fmt: str = Query("json")):
    await websocket.accept()

    try:
        while True:
            event = await websocket.receive()

            if event["type"] == "websocket.disconnect":
                break

            incoming = event.get("text")
            if incoming is None:
                incoming = event.get("bytes")

            if incoming is None:
                continue

            try:
                decoded = BrokerSerializer.decode(incoming, fmt)
                message = BrokerMessage.model_validate(decoded)
            except Exception as exc:
                try:
                    await _send_error(websocket, fmt, f"Invalid message: {exc}")
                except RuntimeError:
                    break
                continue

            if message.action == "subscribe":
                if not message.topic:
                    await _send_error(websocket, fmt, "Missing topic")
                    continue

                await manager.connect(websocket, message.topic)

                undelivered = repo.get_undelivered_by_topic(message.topic)

                for item in undelivered:
                    payload = BrokerSerializer.decode(item.payload, item.format)

                    deliver = DeliverMessage(
                        topic=item.topic,
                        message_id=item.id,
                        payload=payload,
                    )

                    await _send(websocket, fmt, deliver.model_dump())

            elif message.action == "publish":
                if not message.topic:
                    await _send_error(websocket, fmt, "Missing topic")
                    continue

                stored_payload = BrokerSerializer.encode(
                    message.payload,
                    fmt,
                )

                if isinstance(stored_payload, str):
                    stored_payload = stored_payload.encode("utf-8")

                queued = QueuedMessageModel(
                    topic=message.topic,
                    payload=stored_payload,
                    format=fmt,
                    created_at=datetime.utcnow(),
                    is_delivered=False,
                )

                queued = repo.add(queued)

                deliver = DeliverMessage(
                    topic=message.topic,
                    message_id=queued.id,
                    payload=message.payload,
                )

                encoded_deliver = BrokerSerializer.encode(
                    deliver.model_dump(),
                    fmt,
                )

                await manager.broadcast(message.topic, encoded_deliver)

            elif message.action == "ack":
                if message.message_id is None:
                    await _send_error(websocket, fmt, "Missing message_id")
                    continue

                repo.mark_delivered(message.message_id)

            else:
                await _send_error(websocket, fmt, "Unknown action")

    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(websocket)