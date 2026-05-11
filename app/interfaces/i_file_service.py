from abc import ABC, abstractmethod
from typing import BinaryIO, List

from app.core.file_dto import FileUploadResponseDto, FileListItemDto
from app.models.file_model import FileModel


class IFileService(ABC):
    @abstractmethod
    def upload_file(
        self,
        user_id: str,
        bucket_id: int,
        filename: str,
        file_content: BinaryIO,
        content_type: str | None = None,
        is_internal: bool = False,
    ) -> FileUploadResponseDto:
        pass

    @abstractmethod
    def get_files(self, user_id: str) -> List[FileListItemDto]:
        pass

    @abstractmethod
    def get_bucket_files(self, bucket_id: int) -> List[FileListItemDto]:
        pass

    @abstractmethod
    def get_file_for_download(
        self,
        user_id: str,
        file_id: str,
        is_internal: bool = False,
    ) -> FileModel:
        pass

    @abstractmethod
    def delete_file(self, user_id: str, file_id: str) -> None:
        pass