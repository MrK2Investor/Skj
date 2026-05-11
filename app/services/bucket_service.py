from datetime import datetime, UTC

from fastapi import HTTPException

from app.core.bucket_dto import (
    BucketResponseDto,
    BucketBillingResponseDto,
    BucketObjectListResponseDto,
    BucketObjectItemDto,
)
from app.interfaces.i_bucket_service import IBucketService
from app.interfaces.i_bucket_repository import IBucketRepository
from app.interfaces.i_file_repository import IFileRepository
from app.models.bucket_model import BucketModel


class BucketService(IBucketService):
    def __init__(
        self,
        bucket_repository: IBucketRepository,
        file_repository: IFileRepository,
    ):
        self._bucket_repository = bucket_repository
        self._file_repository = file_repository

    def create_bucket(self, name: str) -> BucketResponseDto:
        normalized_name = name.strip()

        if not normalized_name:
            raise HTTPException(status_code=400, detail="Bucket name must not be empty")

        if self._bucket_repository.get_by_name(normalized_name):
            raise HTTPException(status_code=409, detail="Bucket with this name already exists")

        bucket = BucketModel(
            name=normalized_name,
            created_at=datetime.now(UTC),
            bandwidth_bytes=0,
            current_storage_bytes=0,
            ingress_bytes=0,
            egress_bytes=0,
            internal_transfer_bytes=0,
            count_write_requests=0,
            count_read_requests=0,
        )

        self._bucket_repository.add(bucket)

        return BucketResponseDto.model_validate(bucket)

    def get_bucket_objects(self, bucket_id: int) -> BucketObjectListResponseDto:
        bucket = self._bucket_repository.get_by_id(bucket_id)

        if not bucket:
            raise HTTPException(status_code=404, detail="Bucket not found")

        bucket.count_read_requests += 1
        self._bucket_repository.update(bucket)

        objects = self._file_repository.get_by_bucket_id(bucket_id)

        return BucketObjectListResponseDto(
            items=[BucketObjectItemDto.model_validate(obj) for obj in objects],
            total=len(objects),
        )

    def get_bucket_billing(self, bucket_id: int) -> BucketBillingResponseDto:
        bucket = self._bucket_repository.get_by_id(bucket_id)

        if not bucket:
            raise HTTPException(status_code=404, detail="Bucket not found")

        bucket.count_read_requests += 1
        self._bucket_repository.update(bucket)

        bucket.bandwidth_bytes = bucket.ingress_bytes + bucket.egress_bytes
        self._bucket_repository.update(bucket)

        return BucketBillingResponseDto(
            bucket_id=bucket.id,
            bucket_name=bucket.name,
            bandwidth_bytes=bucket.bandwidth_bytes,
            current_storage_bytes=bucket.current_storage_bytes,
            ingress_bytes=bucket.ingress_bytes,
            egress_bytes=bucket.egress_bytes,
            internal_transfer_bytes=bucket.internal_transfer_bytes,
            count_write_requests=bucket.count_write_requests,
            count_read_requests=bucket.count_read_requests,
        )