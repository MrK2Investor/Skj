from datetime import datetime
from pydantic import BaseModel

class ObjectResponse(BaseModel):
    object_id: str
    user_id: str
    filename: str
    content_type: str
    status: str
    volume_id: int | None
    offset: int | None
    size: int | None
    billed_credits: int
    is_deleted: bool
    created_at: datetime
    ready_at: datetime | None
    deleted_at: datetime | None

    class Config:
        from_attributes = True

class BillingAccountResponse(BaseModel):
    user_id: str
    credits: int
    used_storage_bytes: int
    ingress_bytes: int
    egress_bytes: int
    created_at: datetime

    class Config:
        from_attributes = True

class BillingEventResponse(BaseModel):
    id: int
    user_id: str
    object_id: str | None
    event_type: str
    bytes_count: int
    credits_delta: int
    created_at: datetime

    class Config:
        from_attributes = True
