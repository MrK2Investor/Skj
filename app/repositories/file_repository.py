from typing import List, Optional

from app.core.database import SessionLocal
from app.interfaces.i_file_repository import IFileRepository
from app.models.file_model import FileModel


class FileRepository(IFileRepository):
    def __init__(self):
        self._session_factory = SessionLocal

    def add(self, file_model: FileModel) -> None:
        with self._session_factory() as session:
            session.add(file_model)
            session.commit()
            session.refresh(file_model)

    def get_by_id(self, file_id: str) -> Optional[FileModel]:
        with self._session_factory() as session:
            return session.query(FileModel).filter(FileModel.id == file_id).first()

    def get_by_user_id(self, user_id: str) -> List[FileModel]:
        with self._session_factory() as session:
            return (
                session.query(FileModel)
                .filter(FileModel.user_id == user_id, FileModel.is_deleted == False)
                .order_by(FileModel.created_at.desc())
                .all()
            )

    def get_by_bucket_id(self, bucket_id: int, include_deleted: bool = False) -> List[FileModel]:
        with self._session_factory() as session:
            query = session.query(FileModel).filter(FileModel.bucket_id == bucket_id)
            if not include_deleted:
                query = query.filter(FileModel.is_deleted == False)

            return query.order_by(FileModel.created_at.desc()).all()

    def update(self, file_model: FileModel) -> None:
        with self._session_factory() as session:
            existing = session.query(FileModel).filter(FileModel.id == file_model.id).first()
            if existing is None:
                return

            existing.user_id = file_model.user_id
            existing.bucket_id = file_model.bucket_id
            existing.filename = file_model.filename
            existing.path = file_model.path
            existing.size = file_model.size
            existing.created_at = file_model.created_at
            existing.is_deleted = file_model.is_deleted

            session.commit()