import shutil
import uuid
from datetime import datetime, UTC
from pathlib import Path
from typing import BinaryIO, List

from fastapi import HTTPException

from app.core.config import Config
from app.core.file_dto import FileUploadResponseDto, FileListItemDto
from app.models.file_model import FileModel


class FileService:
    MAX_FILENAME_LENGTH = 255
    ALLOWED_CONTENT_TYPES = {
        "text/plain",
        "application/pdf",
        "image/png",
        "image/jpeg",
        "application/json",
        "application/octet-stream",
    }

    def __init__(self, file_repository, bucket_repository):
        self._file_repository = file_repository
        self._bucket_repository = bucket_repository
        Config.STORAGE_DIR.mkdir(parents=True, exist_ok=True)

    # -----------------------------
    # UPLOAD (WRITE)
    # -----------------------------
    def upload_file(
        self,
        user_id: str,
        bucket_id: int,
        filename: str,
        file_content: BinaryIO,
        content_type: str | None = None,
        is_internal: bool = False,
    ) -> FileUploadResponseDto:

        bucket = self._bucket_repository.get_by_id(bucket_id)
        if not bucket:
            raise HTTPException(status_code=404, detail="Bucket not found")

        if not filename or not filename.strip():
            raise HTTPException(status_code=400, detail="Filename must not be empty")

        filename = filename.strip()

        if len(filename) > self.MAX_FILENAME_LENGTH:
            raise HTTPException(status_code=400, detail="Filename too long")

        if content_type and content_type not in self.ALLOWED_CONTENT_TYPES:
            raise HTTPException(status_code=400, detail="Unsupported content type")

        file_id = str(uuid.uuid4())

        user_dir = Config.STORAGE_DIR / str(bucket_id) / user_id
        user_dir.mkdir(parents=True, exist_ok=True)

        file_path = user_dir / file_id

        with open(file_path, "wb") as output_file:
            shutil.copyfileobj(file_content, output_file)

        size = file_path.stat().st_size

        if size == 0:
            file_path.unlink(missing_ok=True)
            raise HTTPException(status_code=400, detail="Empty file")

        file_model = FileModel(
            id=file_id,
            user_id=user_id,
            bucket_id=bucket_id,
            filename=filename,
            path=str(file_path),
            size=size,
            created_at=datetime.now(UTC),
            is_deleted=False,
        )

        self._file_repository.add(file_model)

        # billing
        bucket.current_storage_bytes += size

        if is_internal:
            bucket.internal_transfer_bytes += size
        else:
            bucket.ingress_bytes += size

        bucket.bandwidth_bytes = bucket.ingress_bytes + bucket.egress_bytes

        bucket.count_write_requests += 1
        self._bucket_repository.update(bucket)

        return FileUploadResponseDto(
            id=file_model.id,
            filename=file_model.filename,
            size=file_model.size,
            bucket_id=file_model.bucket_id,
        )

    # -----------------------------
    # LIST FILES (READ)
    # -----------------------------
    def get_files(self, user_id: str) -> List[FileListItemDto]:
        files = self._file_repository.get_by_user_id(user_id)

        counted = set()

        for file in files:
            if file.bucket_id not in counted:
                bucket = self._bucket_repository.get_by_id(file.bucket_id)

                if bucket:
                    bucket.count_read_requests += 1
                    self._bucket_repository.update(bucket)

                counted.add(file.bucket_id)

        return [FileListItemDto.model_validate(f) for f in files]

    # -----------------------------
    # DOWNLOAD (READ)
    # -----------------------------
    def get_file_for_download(
        self,
        user_id: str,
        file_id: str,
        is_internal: bool = False,
    ) -> FileModel:

        file_model = self._file_repository.get_by_id(file_id)

        if not file_model or file_model.is_deleted:
            raise HTTPException(status_code=404)

        if file_model.user_id != user_id:
            raise HTTPException(status_code=403)

        file_path = Path(file_model.path)
        if not file_path.exists():
            raise HTTPException(status_code=404)

        bucket = self._bucket_repository.get_by_id(file_model.bucket_id)

        if bucket:
            if is_internal:
                bucket.internal_transfer_bytes += file_model.size
            else:
                bucket.egress_bytes += file_model.size

            bucket.bandwidth_bytes = bucket.ingress_bytes + bucket.egress_bytes

            bucket.count_read_requests += 1
            self._bucket_repository.update(bucket)

        return file_model

    # -----------------------------
    # DELETE (WRITE)
    # -----------------------------
    def delete_file(self, user_id: str, file_id: str) -> None:

        file_model = self._file_repository.get_by_id(file_id)

        if not file_model or file_model.is_deleted:
            raise HTTPException(status_code=404)

        if file_model.user_id != user_id:
            raise HTTPException(status_code=403)

        file_model.is_deleted = True
        self._file_repository.update(file_model)

        bucket = self._bucket_repository.get_by_id(file_model.bucket_id)

        if bucket:
            bucket.count_write_requests += 1
            self._bucket_repository.update(bucket)