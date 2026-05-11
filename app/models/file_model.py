from datetime import datetime

from sqlalchemy import String, Integer, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class FileModel(Base):
    __tablename__ = "files"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(String, index=True)
    bucket_id: Mapped[int] = mapped_column(ForeignKey("buckets.id"), index=True)
    filename: Mapped[str] = mapped_column(String(255))
    path: Mapped[str] = mapped_column(String)
    size: Mapped[int] = mapped_column(Integer)

    # FIX
    created_at: Mapped[datetime] = mapped_column(DateTime)

    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)

    bucket = relationship("BucketModel", back_populates="objects")