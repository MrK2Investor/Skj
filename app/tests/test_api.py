import io
import time

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def unique_bucket_name() -> str:
    return f"bucket-{int(time.time() * 1000)}"


def create_bucket() -> int:
    response = client.post("/buckets/", json={"name": unique_bucket_name()})
    assert response.status_code == 200, response.text
    return response.json()["id"]


def upload_file(
    bucket_id: int,
    user_id: str,
    content: bytes,
    filename: str = "a.txt",
    internal: bool = False,
):
    headers = {
        "x-user-id": user_id,
        "bucket-id": str(bucket_id),
    }
    if internal:
        headers["x-internal-source"] = "true"

    files = {
        "file": (filename, io.BytesIO(content), "text/plain")
    }

    return client.post("/files/upload", headers=headers, files=files)


def test_create_bucket() -> None:
    response = client.post("/buckets/", json={"name": unique_bucket_name()})
    assert response.status_code == 200, response.text

    data = response.json()
    assert "id" in data
    assert "name" in data


def test_upload_and_list_files() -> None:
    bucket_id = create_bucket()

    upload_response = upload_file(bucket_id, "user-a", b"hello world", "hello.txt")
    assert upload_response.status_code == 200, upload_response.text

    list_response = client.get("/files", headers={"x-user-id": "user-a"})
    assert list_response.status_code == 200, list_response.text

    items = list_response.json()
    assert len(items) >= 1
    assert any(item["filename"] == "hello.txt" for item in items)


def test_bucket_objects_contains_uploaded_file() -> None:
    bucket_id = create_bucket()

    upload_response = upload_file(bucket_id, "user-b", b"bucket file", "bucket.txt")
    assert upload_response.status_code == 200, upload_response.text

    objects_response = client.get(f"/buckets/{bucket_id}/objects")
    assert objects_response.status_code == 200, objects_response.text

    data = objects_response.json()
    assert data["total"] >= 1
    assert any(item["filename"] == "bucket.txt" for item in data["items"])


def test_billing_after_external_upload() -> None:
    bucket_id = create_bucket()

    content = b"1234567890"
    upload_response = upload_file(bucket_id, "user-c", content, "bill.txt", internal=False)
    assert upload_response.status_code == 200, upload_response.text

    billing_response = client.get(f"/buckets/{bucket_id}/billing")
    assert billing_response.status_code == 200, billing_response.text

    billing = billing_response.json()
    assert billing["current_storage_bytes"] >= len(content)
    assert billing["ingress_bytes"] >= len(content)
    assert billing["count_write_requests"] >= 1


def test_billing_after_internal_upload() -> None:
    bucket_id = create_bucket()

    content = b"internal-data"
    upload_response = upload_file(bucket_id, "user-d", content, "internal.txt", internal=True)
    assert upload_response.status_code == 200, upload_response.text

    billing_response = client.get(f"/buckets/{bucket_id}/billing")
    assert billing_response.status_code == 200, billing_response.text

    billing = billing_response.json()
    assert billing["current_storage_bytes"] >= len(content)
    assert billing["internal_transfer_bytes"] >= len(content)


def test_download_increases_egress() -> None:
    bucket_id = create_bucket()

    content = b"download-me"
    upload_response = upload_file(bucket_id, "user-e", content, "download.txt", internal=False)
    assert upload_response.status_code == 200, upload_response.text

    file_id = upload_response.json()["id"]

    before = client.get(f"/buckets/{bucket_id}/billing").json()["egress_bytes"]

    download_response = client.get(
        f"/files/{file_id}",
        headers={"x-user-id": "user-e"},
    )
    assert download_response.status_code == 200, download_response.text

    after = client.get(f"/buckets/{bucket_id}/billing").json()["egress_bytes"]
    assert after >= before + len(content)


def test_soft_delete_hides_file_from_list() -> None:
    bucket_id = create_bucket()

    upload_response = upload_file(bucket_id, "user-f", b"to-delete", "delete.txt")
    assert upload_response.status_code == 200, upload_response.text

    file_id = upload_response.json()["id"]

    delete_response = client.delete(
        f"/files/{file_id}",
        headers={"x-user-id": "user-f"},
    )
    assert delete_response.status_code == 200, delete_response.text

    list_response = client.get("/files", headers={"x-user-id": "user-f"})
    assert list_response.status_code == 200, list_response.text

    items = list_response.json()
    assert all(item["id"] != file_id for item in items)


def test_file_access_denied_for_other_user() -> None:
    bucket_id = create_bucket()

    upload_response = upload_file(bucket_id, "owner-user", b"secret", "secret.txt")
    assert upload_response.status_code == 200, upload_response.text

    file_id = upload_response.json()["id"]

    download_response = client.get(
        f"/files/{file_id}",
        headers={"x-user-id": "other-user"},
    )
    assert download_response.status_code == 403, download_response.text

def test_external_upload_increases_ingress() -> None:
    bucket_id = create_bucket()

    upload_response = upload_file(
        bucket_id=bucket_id,
        user_id="user-external",
        content=b"hello",
        filename="external.txt",
    )

    assert upload_response.status_code == 200

    billing_response = client.get(f"/buckets/{bucket_id}/billing")
    assert billing_response.status_code == 200

    data = billing_response.json()

    assert data["ingress_bytes"] == 5
    assert data["internal_transfer_bytes"] == 0
    assert data["current_storage_bytes"] == 5
    assert data["count_write_requests"] == 1


def test_internal_upload_increases_internal_transfer() -> None:
    bucket_id = create_bucket()

    upload_response = client.post(
        "/files/upload",
        headers={
            "x-user-id": "user-internal",
            "bucket-id": str(bucket_id),
            "x-internal-source": "true",
        },
        files={
            "file": ("internal.txt", b"hello", "text/plain"),
        },
    )

    assert upload_response.status_code == 200

    billing_response = client.get(f"/buckets/{bucket_id}/billing")
    assert billing_response.status_code == 200

    data = billing_response.json()

    assert data["ingress_bytes"] == 0
    assert data["internal_transfer_bytes"] == 5
    assert data["current_storage_bytes"] == 5
    assert data["count_write_requests"] == 1


def test_external_download_increases_egress_and_read_count() -> None:
    bucket_id = create_bucket()

    upload_response = upload_file(
        bucket_id=bucket_id,
        user_id="user-download",
        content=b"hello",
        filename="download.txt",
    )

    file_id = upload_response.json()["id"]

    download_response = client.get(
        f"/files/{file_id}",
        headers={"x-user-id": "user-download"},
    )

    assert download_response.status_code == 200

    billing_response = client.get(f"/buckets/{bucket_id}/billing")
    assert billing_response.status_code == 200

    data = billing_response.json()

    assert data["ingress_bytes"] == 5
    assert data["egress_bytes"] == 5
    assert data["internal_transfer_bytes"] == 0
    assert data["count_write_requests"] == 1

    # +1 download, +1 billing request
    assert data["count_read_requests"] >= 2


def test_internal_download_increases_internal_transfer_not_egress() -> None:
    bucket_id = create_bucket()

    upload_response = upload_file(
        bucket_id=bucket_id,
        user_id="user-internal-download",
        content=b"hello",
        filename="internal-download.txt",
    )

    file_id = upload_response.json()["id"]

    download_response = client.get(
        f"/files/{file_id}",
        headers={
            "x-user-id": "user-internal-download",
            "x-internal-source": "true",
        },
    )

    assert download_response.status_code == 200

    billing_response = client.get(f"/buckets/{bucket_id}/billing")
    assert billing_response.status_code == 200

    data = billing_response.json()

    assert data["ingress_bytes"] == 5
    assert data["egress_bytes"] == 0
    assert data["internal_transfer_bytes"] == 5
    assert data["count_write_requests"] == 1

    # +1 download, +1 billing request
    assert data["count_read_requests"] >= 2