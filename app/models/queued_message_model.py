from datetime import datetime

from sqlalchemy import String, DateTime, Boolean, LargeBinary
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class QueuedMessageModel(Base):
    __tablename__ = "queued_messages"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    topic: Mapped[str] = mapped_column(String(100), index=True)
    payload: Mapped[bytes] = mapped_column(LargeBinary)
    format: Mapped[str] = mapped_column(String(20), default="json")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    is_delivered: Mapped[bool] = mapped_column(Boolean, default=False)