from typing import Annotated, List

from fastapi import APIRouter, Header, UploadFile, File
from fastapi.responses import FileResponse

from app.core.file_dto import (
    FileUploadResponseDto,
    FileListItemDto,
    DeleteFileResponseDto,
)
from app.repositories.file_repository import FileRepository
from app.repositories.bucket_repository import BucketRepository
from app.services.file_service import FileService

router = APIRouter(prefix="/files", tags=["Files"])

file_repository = FileRepository()
bucket_repository = BucketRepository()
file_service = FileService(file_repository, bucket_repository)


@router.post("/upload", response_model=FileUploadResponseDto)
def upload_file(
    file: UploadFile = File(..., description="File to upload"),
    bucket_id: int = Header(...),
    x_user_id: Annotated[str, Header(min_length=1, max_length=255)] = "",
    x_internal_source: Annotated[str | None, Header()] = None,
):
    is_internal = (x_internal_source or "").lower() == "true"

    return file_service.upload_file(
        user_id=x_user_id,
        bucket_id=bucket_id,
        filename=file.filename or "",
        file_content=file.file,
        content_type=file.content_type,
        is_internal=is_internal,
    )


@router.get("", response_model=List[FileListItemDto])
def get_files(
    x_user_id: Annotated[str, Header(min_length=1, max_length=255)] = "",
):
    return file_service.get_files(x_user_id)


@router.get("/{file_id}")
def download_file(
    file_id: str,
    x_user_id: Annotated[str, Header(min_length=1, max_length=255)] = "",
    x_internal_source: Annotated[str | None, Header()] = None,
):
    is_internal = (x_internal_source or "").lower() == "true"

    file_model = file_service.get_file_for_download(
        user_id=x_user_id,
        file_id=file_id,
        is_internal=is_internal,
    )

    return FileResponse(
        path=file_model.path,
        filename=file_model.filename,
        media_type="application/octet-stream",
    )


@router.delete("/{file_id}", response_model=DeleteFileResponseDto)
def delete_file(
    file_id: str,
    x_user_id: Annotated[str, Header(min_length=1, max_length=255)] = "",
):
    file_service.delete_file(x_user_id, file_id)
    return DeleteFileResponseDto(message="File deleted successfully")