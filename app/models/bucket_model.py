from datetime import datetime

from sqlalchemy import String, Integer, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class BucketModel(Base):
    __tablename__ = "buckets"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # billing
    bandwidth_bytes: Mapped[int] = mapped_column(Integer, default=0)

    current_storage_bytes: Mapped[int] = mapped_column(Integer, default=0)
    ingress_bytes: Mapped[int] = mapped_column(Integer, default=0)
    egress_bytes: Mapped[int] = mapped_column(Integer, default=0)
    internal_transfer_bytes: Mapped[int] = mapped_column(Integer, default=0)

    count_write_requests: Mapped[int] = mapped_column(Integer, default=0)
    count_read_requests: Mapped[int] = mapped_column(Integer, default=0)

    objects = relationship("FileModel", back_populates="bucket")