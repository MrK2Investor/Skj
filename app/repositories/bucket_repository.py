from typing import Optional, List

from app.core.database import SessionLocal
from app.interfaces.i_bucket_repository import IBucketRepository
from app.models.bucket_model import BucketModel


class BucketRepository(IBucketRepository):
    def __init__(self):
        self._session_factory = SessionLocal

    def add(self, bucket_model: BucketModel) -> None:
        with self._session_factory() as session:
            session.add(bucket_model)
            session.commit()
            session.refresh(bucket_model)

    def get_by_id(self, bucket_id: int) -> Optional[BucketModel]:
        with self._session_factory() as session:
            return session.query(BucketModel).filter(BucketModel.id == bucket_id).first()

    def get_by_name(self, name: str) -> Optional[BucketModel]:
        with self._session_factory() as session:
            return session.query(BucketModel).filter(BucketModel.name == name).first()

    def list_all(self) -> List[BucketModel]:
        with self._session_factory() as session:
            return session.query(BucketModel).order_by(BucketModel.created_at.desc()).all()

    def update(self, bucket_model: BucketModel) -> None:
        with self._session_factory() as session:
            existing = session.query(BucketModel).filter(BucketModel.id == bucket_model.id).first()
            if existing is None:
                return

            existing.name = bucket_model.name
            existing.bandwidth_bytes = bucket_model.bandwidth_bytes
            existing.current_storage_bytes = bucket_model.current_storage_bytes
            existing.ingress_bytes = bucket_model.ingress_bytes
            existing.egress_bytes = bucket_model.egress_bytes
            existing.internal_transfer_bytes = bucket_model.internal_transfer_bytes
            existing.count_write_requests = bucket_model.count_write_requests
            existing.count_read_requests = bucket_model.count_read_requests

            session.commit()