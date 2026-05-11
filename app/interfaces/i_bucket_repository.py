from abc import ABC, abstractmethod
from typing import Optional, List

from app.models.bucket_model import BucketModel


class IBucketRepository(ABC):
    @abstractmethod
    def add(self, bucket_model: BucketModel) -> None:
        pass

    @abstractmethod
    def get_by_id(self, bucket_id: int) -> Optional[BucketModel]:
        pass

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[BucketModel]:
        pass

    @abstractmethod
    def list_all(self) -> List[BucketModel]:
        pass

    @abstractmethod
    def update(self, bucket_model: BucketModel) -> None:
        pass