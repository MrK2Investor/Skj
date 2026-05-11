from datetime import datetime

from pydantic import BaseModel, ConfigDict


class FileUploadResponseDto(BaseModel):
    id: str
    filename: str
    size: int
    bucket_id: int

    model_config = ConfigDict(from_attributes=True)


class FileListItemDto(BaseModel):
    id: str
    user_id: str
    bucket_id: int
    filename: str
    path: str
    size: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DeleteFileResponseDto(BaseModel):
    message: str