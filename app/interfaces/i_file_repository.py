from abc import ABC, abstractmethod
from typing import Optional, List

from app.models.file_model import FileModel


class IFileRepository(ABC):
    @abstractmethod
    def add(self, file_model: FileModel) -> None:
        pass

    @abstractmethod
    def get_by_id(self, file_id: str) -> Optional[FileModel]:
        pass

    @abstractmethod
    def get_by_user_id(self, user_id: str) -> List[FileModel]:
        pass

    @abstractmethod
    def get_by_bucket_id(self, bucket_id: int, include_deleted: bool = False) -> List[FileModel]:
        pass
    
    @abstractmethod
    def update(self, file_model: FileModel) -> None:
        pass