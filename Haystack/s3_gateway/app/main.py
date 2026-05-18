from __future__ import annotations

import asyncio
from datetime import datetime
from uuid import uuid4

import httpx
from fastapi import Depends, FastAPI, File, Header, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from sqlalchemy.orm import Session

from .billing import (
    commit_download_billing,
    commit_upload_billing,
    get_or_create_account,
    refund_storage_on_soft_delete,
)
from .broker_client import BrokerClient
from .config import settings
from .database import Base, SessionLocal, engine, get_db
from .models import BillingEvent, StoredObject
from .schemas import BillingAccountResponse, BillingEventResponse, ObjectResponse

app = FastAPI(title="Appify S3 Gateway")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)


async def storage_ack_listener():
    while True:
        try:
            client = BrokerClient(settings.broker_url)
            await client.connect()
            await client.subscribe("storage.ack")

            async for msg in client.listen():
                ack = msg.get("payload", {})
                object_id = ack.get("object_id")

                if not object_id:
                    continue

                db = SessionLocal()

                try:
                    obj = db.get(StoredObject, object_id)

                    if obj and not obj.is_deleted:
                        obj.volume_id = int(ack["volume_id"])
                        obj.offset = int(ack["offset"])
                        obj.size = int(ack["size"])
                        obj.ready_at = datetime.utcnow()

                        if commit_upload_billing(db, obj, obj.size):
                            obj.status = "ready"
                        else:
                            obj.status = "payment_required"

                        db.commit()

                finally:
                    db.close()

        except Exception:
            await asyncio.sleep(2)


@app.on_event("startup")
async def startup():
    asyncio.create_task(storage_ack_listener())


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/upload", response_model=ObjectResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload(
    file: UploadFile = File(...),
    x_user_id: str = Header(default="demo-user"),
    db: Session = Depends(get_db),
):
    data = await file.read()

    if not data:
        raise HTTPException(status_code=400, detail="Empty file is not allowed")

    get_or_create_account(db, x_user_id)

    object_id = str(uuid4())

    obj = StoredObject(
        object_id=object_id,
        user_id=x_user_id,
        filename=file.filename or object_id,
        content_type=file.content_type or "application/octet-stream",
        status="uploading",
        is_deleted=False,
    )

    db.add(obj)
    db.commit()
    db.refresh(obj)

    client = BrokerClient(settings.broker_url)
    await client.connect()

    try:
        await client.publish(
            "storage.write",
            {
                "object_id": object_id,
                "data": data,
            },
        )
    finally:
        await client.close()

    return obj


@app.get("/objects", response_model=list[ObjectResponse])
def list_objects(
    x_user_id: str = Header(default="demo-user"),
    db: Session = Depends(get_db),
):
    return (
        db.query(StoredObject)
        .filter(
            StoredObject.user_id == x_user_id,
            StoredObject.is_deleted == False,  # noqa: E712
        )
        .order_by(StoredObject.created_at.desc())
        .all()
    )


@app.get("/objects/{object_id}", response_model=ObjectResponse)
def get_object(
    object_id: str,
    x_user_id: str = Header(default="demo-user"),
    db: Session = Depends(get_db),
):
    obj = db.get(StoredObject, object_id)

    if not obj or obj.is_deleted or obj.user_id != x_user_id:
        raise HTTPException(status_code=404, detail="Object not found")

    return obj


@app.get("/download/{object_id}")
async def download(
    object_id: str,
    x_user_id: str = Header(default="demo-user"),
    db: Session = Depends(get_db),
):
    obj = db.get(StoredObject, object_id)

    if not obj or obj.is_deleted or obj.user_id != x_user_id:
        raise HTTPException(status_code=404, detail="Object not found")

    if obj.status == "payment_required":
        raise HTTPException(status_code=402, detail="Not enough credits to finalize this upload")

    if obj.status != "ready":
        raise HTTPException(status_code=409, detail="Object is not ready yet")

    if obj.volume_id is None or obj.offset is None or obj.size is None:
        raise HTTPException(status_code=500, detail="Object metadata is incomplete")

    if not commit_download_billing(db, obj, obj.size):
        db.commit()
        raise HTTPException(status_code=402, detail="Not enough credits for download")

    db.commit()

    url = f"{settings.haystack_url}/volume/{obj.volume_id}/{obj.offset}/{obj.size}"

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(url)

        if resp.status_code != 200:
            raise HTTPException(status_code=502, detail="Haystack node failed")

        return Response(content=resp.content, media_type=obj.content_type)


@app.delete("/download/{object_id}")
def soft_delete(
    object_id: str,
    x_user_id: str = Header(default="demo-user"),
    db: Session = Depends(get_db),
):
    obj = db.get(StoredObject, object_id)

    if not obj or obj.is_deleted or obj.user_id != x_user_id:
        raise HTTPException(status_code=404, detail="Object not found")

    obj.is_deleted = True
    obj.deleted_at = datetime.utcnow()

    refund_storage_on_soft_delete(db, obj)

    db.commit()

    return {
        "object_id": object_id,
        "is_deleted": True,
    }


@app.post("/image/process/{object_id}", response_model=ObjectResponse, status_code=status.HTTP_202_ACCEPTED)
async def process_image(
    object_id: str,
    action: str = "grayscale",
    x_user_id: str = Header(default="demo-user"),
    db: Session = Depends(get_db),
):
    obj = db.get(StoredObject, object_id)

    if not obj or obj.is_deleted or obj.user_id != x_user_id:
        raise HTTPException(status_code=404, detail="Object not found")

    if obj.status == "payment_required":
        raise HTTPException(status_code=402, detail="Object was not paid/finalized")

    if obj.status != "ready":
        raise HTTPException(status_code=409, detail="Object is not ready yet")

    if obj.volume_id is None or obj.offset is None or obj.size is None:
        raise HTTPException(status_code=500, detail="Object metadata is incomplete")

    if action not in ["grayscale"]:
        raise HTTPException(status_code=400, detail="Unsupported image action")

    if not commit_download_billing(db, obj, obj.size):
        db.commit()
        raise HTTPException(status_code=402, detail="Not enough credits for image processing input")

    db.commit()

    haystack_url = f"{settings.haystack_url}/volume/{obj.volume_id}/{obj.offset}/{obj.size}"

    async with httpx.AsyncClient(timeout=60) as client:
        source_resp = await client.get(haystack_url)

        if source_resp.status_code != 200:
            raise HTTPException(status_code=502, detail="Haystack node failed")

        files = {
            "file": (
                obj.filename,
                source_resp.content,
                obj.content_type or "application/octet-stream",
            )
        }

        worker_resp = await client.post(
            f"{settings.image_worker_url}/image/{action}",
            files=files,
        )

        if worker_resp.status_code != 200:
            raise HTTPException(status_code=502, detail="Image worker failed")

        processed_data = worker_resp.content

    new_object_id = str(uuid4())
    new_filename = f"{action}_{obj.filename}"

    new_obj = StoredObject(
        object_id=new_object_id,
        user_id=x_user_id,
        filename=new_filename,
        content_type=obj.content_type or "image/jpeg",
        status="uploading",
        is_deleted=False,
    )

    db.add(new_obj)
    db.commit()
    db.refresh(new_obj)

    broker = BrokerClient(settings.broker_url)
    await broker.connect()

    try:
        await broker.publish(
            "storage.write",
            {
                "object_id": new_object_id,
                "data": processed_data,
            },
        )
    finally:
        await broker.close()

    return new_obj


@app.get("/billing/account", response_model=BillingAccountResponse)
def billing_account(
    x_user_id: str = Header(default="demo-user"),
    db: Session = Depends(get_db),
):
    account = get_or_create_account(db, x_user_id)
    db.commit()
    db.refresh(account)

    return account


@app.get("/billing/events", response_model=list[BillingEventResponse])
def billing_events(
    x_user_id: str = Header(default="demo-user"),
    db: Session = Depends(get_db),
):
    return (
        db.query(BillingEvent)
        .filter(BillingEvent.user_id == x_user_id)
        .order_by(BillingEvent.created_at.desc())
        .limit(100)
        .all()
    )


@app.post("/admin/billing/{user_id}/credits")
def add_credits(
    user_id: str,
    payload: dict,
    db: Session = Depends(get_db),
    x_admin_token: str | None = Header(default=None),
):
    if x_admin_token != settings.admin_token:
        raise HTTPException(status_code=401, detail="Invalid admin token")

    amount = int(payload.get("amount", 0))

    if amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")

    account = get_or_create_account(db, user_id)
    account.credits += amount

    db.add(
        BillingEvent(
            user_id=user_id,
            object_id=None,
            event_type="admin_credit_topup",
            bytes_count=0,
            credits_delta=amount,
        )
    )

    db.commit()

    return {
        "user_id": user_id,
        "credits": account.credits,
    }


@app.get("/admin/volumes/{volume_id}/live-objects")
def live_objects(
    volume_id: int,
    db: Session = Depends(get_db),
    x_admin_token: str | None = Header(default=None),
):
    if x_admin_token != settings.admin_token:
        raise HTTPException(status_code=401, detail="Invalid admin token")

    objects = (
        db.query(StoredObject)
        .filter(
            StoredObject.volume_id == volume_id,
            StoredObject.status == "ready",
            StoredObject.is_deleted == False,  # noqa: E712
        )
        .order_by(StoredObject.offset.asc())
        .all()
    )

    return {
        "volume_id": volume_id,
        "objects": [
            {
                "object_id": o.object_id,
                "volume_id": o.volume_id,
                "offset": o.offset,
                "size": o.size,
            }
            for o in objects
        ],
    }


@app.post("/admin/objects/{object_id}/location")
def update_location(
    object_id: str,
    payload: dict,
    db: Session = Depends(get_db),
    x_admin_token: str | None = Header(default=None),
):
    if x_admin_token != settings.admin_token:
        raise HTTPException(status_code=401, detail="Invalid admin token")

    obj = db.get(StoredObject, object_id)

    if not obj or obj.is_deleted:
        raise HTTPException(status_code=404, detail="Object not found")

    obj.volume_id = int(payload["volume_id"])
    obj.offset = int(payload["offset"])
    obj.size = int(payload["size"])
    obj.status = "ready"

    db.commit()

    return {
        "updated": True,
        "object_id": object_id,
    }