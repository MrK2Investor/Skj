from typing import Any, Literal

from pydantic import BaseModel


class BrokerMessage(BaseModel):
    action: Literal["subscribe", "publish", "ack"]
    topic: str | None = None
    payload: Any | None = None
    message_id: int | None = None


class DeliverMessage(BaseModel):
    action: Literal["deliver"] = "deliver"
    topic: str
    message_id: int
    payload: Any