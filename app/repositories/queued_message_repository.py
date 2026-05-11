from typing import List, Optional

from app.core.database import SessionLocal
from app.models.queued_message_model import QueuedMessageModel


class QueuedMessageRepository:
    def __init__(self):
        self._session_factory = SessionLocal

    def add(self, message: QueuedMessageModel) -> QueuedMessageModel:
        with self._session_factory() as session:
            session.add(message)
            session.commit()
            session.refresh(message)
            return message

    def get_undelivered_by_topic(self, topic: str) -> List[QueuedMessageModel]:
        with self._session_factory() as session:
            return (
                session.query(QueuedMessageModel)
                .filter(
                    QueuedMessageModel.topic == topic,
                    QueuedMessageModel.is_delivered == False,
                )
                .order_by(QueuedMessageModel.created_at.asc())
                .all()
            )

    def mark_delivered(self, message_id: int) -> None:
        with self._session_factory() as session:
            message = (
                session.query(QueuedMessageModel)
                .filter(QueuedMessageModel.id == message_id)
                .first()
            )

            if message:
                message.is_delivered = True
                session.commit()