from pydantic import BaseModel, Field, ConfigDict


class BucketCreateRequestDto(BaseModel):
    name: str = Field(..., min_length=3, max_length=100)


class BucketResponseDto(BaseModel):
    id: int
    name: str

    model_config = ConfigDict(from_attributes=True)


class BucketObjectItemDto(BaseModel):
    id: str
    filename: str = Field(..., max_length=255)
    size: int = Field(..., ge=0)

    model_config = ConfigDict(from_attributes=True)


class BucketObjectListResponseDto(BaseModel):
    items: list[BucketObjectItemDto]
    total: int = Field(..., ge=0)


class BucketBillingResponseDto(BaseModel):
    bucket_id: int
    bucket_name: str
    bandwidth_bytes: int = Field(..., ge=0)
    current_storage_bytes: int = Field(..., ge=0)
    ingress_bytes: int = Field(..., ge=0)
    egress_bytes: int = Field(..., ge=0)
    internal_transfer_bytes: int = Field(..., ge=0)
    count_write_requests: int = Field(..., ge=0)
    count_read_requests: int = Field(..., ge=0)