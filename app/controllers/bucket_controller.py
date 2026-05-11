from fastapi import APIRouter

from app.repositories.bucket_repository import BucketRepository
from app.repositories.file_repository import FileRepository
from app.services.bucket_service import BucketService
from app.core.bucket_dto import (
    BucketCreateRequestDto,
    BucketResponseDto,
    BucketObjectListResponseDto,
    BucketBillingResponseDto,
)

router = APIRouter(prefix="/buckets", tags=["Buckets"])

bucket_repo = BucketRepository()
file_repo = FileRepository()
bucket_service = BucketService(bucket_repo, file_repo)


@router.post("/", response_model=BucketResponseDto)
def create_bucket(req: BucketCreateRequestDto):
    return bucket_service.create_bucket(req.name)


@router.get("/{bucket_id}/objects", response_model=BucketObjectListResponseDto)
def list_objects(bucket_id: int):
    return bucket_service.get_bucket_objects(bucket_id)


@router.get("/{bucket_id}/billing", response_model=BucketBillingResponseDto)
def billing(bucket_id: int):
    return bucket_service.get_bucket_billing(bucket_id)