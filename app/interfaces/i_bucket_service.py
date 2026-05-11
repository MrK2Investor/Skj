from abc import ABC, abstractmethod

from app.core.bucket_dto import (
    BucketResponseDto,
    BucketBillingResponseDto,
    BucketObjectListResponseDto,
)


class IBucketService(ABC):
    @abstractmethod
    def create_bucket(self, name: str) -> BucketResponseDto:
        pass

    @abstractmethod
    def get_bucket_objects(self, bucket_id: int) -> BucketObjectListResponseDto:
        pass

    @abstractmethod
    def get_bucket_billing(self, bucket_id: int) -> BucketBillingResponseDto:
        pass