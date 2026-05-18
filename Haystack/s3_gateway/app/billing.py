from __future__ import annotations

from math import ceil
from sqlalchemy.orm import Session
from .config import settings
from .models import BillingEvent, StoredObject, UserAccount


def kib_units(size_bytes: int) -> int:
    return max(1, ceil(size_bytes / 1024)) if size_bytes > 0 else 0


def upload_cost(size_bytes: int) -> int:
    return kib_units(size_bytes) * settings.upload_credit_per_kib


def download_cost(size_bytes: int) -> int:
    return kib_units(size_bytes) * settings.download_credit_per_kib


def get_or_create_account(db: Session, user_id: str) -> UserAccount:
    account = db.get(UserAccount, user_id)
    if account is None:
        account = UserAccount(user_id=user_id, credits=settings.initial_credits)
        db.add(account)
        db.flush()
    return account


def commit_upload_billing(db: Session, obj: StoredObject, size_bytes: int) -> bool:
    if obj.billed_credits > 0:
        return True

    account = get_or_create_account(db, obj.user_id)
    cost = upload_cost(size_bytes)
    if account.credits < cost:
        db.add(BillingEvent(
            user_id=obj.user_id,
            object_id=obj.object_id,
            event_type="upload_rejected_insufficient_credits",
            bytes_count=size_bytes,
            credits_delta=0,
        ))
        return False

    account.credits -= cost
    account.used_storage_bytes += size_bytes
    account.ingress_bytes += size_bytes
    obj.billed_credits = cost
    db.add(BillingEvent(
        user_id=obj.user_id,
        object_id=obj.object_id,
        event_type="upload_commit",
        bytes_count=size_bytes,
        credits_delta=-cost,
    ))
    return True


def commit_download_billing(db: Session, obj: StoredObject, size_bytes: int) -> bool:
    account = get_or_create_account(db, obj.user_id)
    cost = download_cost(size_bytes)
    if account.credits < cost:
        db.add(BillingEvent(
            user_id=obj.user_id,
            object_id=obj.object_id,
            event_type="download_rejected_insufficient_credits",
            bytes_count=size_bytes,
            credits_delta=0,
        ))
        return False

    account.credits -= cost
    account.egress_bytes += size_bytes
    db.add(BillingEvent(
        user_id=obj.user_id,
        object_id=obj.object_id,
        event_type="download_egress",
        bytes_count=size_bytes,
        credits_delta=-cost,
    ))
    return True


def refund_storage_on_soft_delete(db: Session, obj: StoredObject) -> None:
    account = get_or_create_account(db, obj.user_id)
    if obj.size:
        account.used_storage_bytes = max(0, account.used_storage_bytes - obj.size)
    db.add(BillingEvent(
        user_id=obj.user_id,
        object_id=obj.object_id,
        event_type="soft_delete",
        bytes_count=obj.size or 0,
        credits_delta=0,
    ))
