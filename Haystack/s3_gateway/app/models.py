from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .database import Base

class UserAccount(Base):
    __tablename__ = "user_accounts"

    user_id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    credits: Mapped[int] = mapped_column(Integer, nullable=False, default=100_000)
    used_storage_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    ingress_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    egress_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    objects: Mapped[list["StoredObject"]] = relationship(back_populates="user")
    billing_events: Mapped[list["BillingEvent"]] = relationship(back_populates="user")

class StoredObject(Base):
    __tablename__ = "objects"

    object_id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("user_accounts.user_id"), nullable=False, index=True)
    filename: Mapped[str] = mapped_column(String, nullable=False)
    content_type: Mapped[str] = mapped_column(String, nullable=False, default="application/octet-stream")
    status: Mapped[str] = mapped_column(String, nullable=False, default="uploading")
    volume_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    offset: Mapped[int | None] = mapped_column(Integer, nullable=True)
    size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    billed_credits: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    ready_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    user: Mapped[UserAccount] = relationship(back_populates="objects")

class BillingEvent(Base):
    __tablename__ = "billing_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("user_accounts.user_id"), nullable=False, index=True)
    object_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    event_type: Mapped[str] = mapped_column(String, nullable=False)  # upload_commit, download_egress, soft_delete_refund
    bytes_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    credits_delta: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    user: Mapped[UserAccount] = relationship(back_populates="billing_events")
