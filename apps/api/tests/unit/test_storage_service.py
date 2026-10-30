from pathlib import Path

import pytest

from app.core.config import Settings
from app.services import storage_service


def test_local_storage_saves_reads_and_deletes_pdf(tmp_path: Path, monkeypatch):
    settings = Settings(storage_local_path=str(tmp_path))
    monkeypatch.setattr(storage_service, "get_settings", lambda: settings)

    key = storage_service.save_pdf(b"%PDF-local")

    assert key.endswith(".pdf")
    assert storage_service.read_file(key) == b"%PDF-local"
    storage_service.delete_file(key)
    with pytest.raises(FileNotFoundError):
        storage_service.read_file(key)


def test_storage_rejects_path_traversal():
    with pytest.raises(ValueError, match="Invalid storage key"):
        storage_service.read_file("../outside.pdf")


def test_s3_storage_saves_reads_and_deletes_pdf(monkeypatch):
    settings = Settings(
        storage_backend="s3",
        storage_s3_endpoint_url="https://account.r2.cloudflarestorage.com",
        storage_s3_bucket="deposit360-documents",
        storage_s3_access_key_id="test-access-key",
        storage_s3_secret_access_key="test-secret-key",
    )

    class FakeS3Client:
        def __init__(self):
            self.objects: dict[str, bytes] = {}
            self.upload_metadata: dict[str, str] = {}
            self.deleted: list[str] = []

        def put_object(self, *, Bucket: str, Key: str, Body: bytes, ContentType: str):
            self.objects[Key] = Body
            self.upload_metadata = {"bucket": Bucket, "content_type": ContentType}

        def get_object(self, *, Bucket: str, Key: str):
            return {"Body": _FakeBody(self.objects[Key])}

        def delete_object(self, *, Bucket: str, Key: str):
            self.deleted.append(Key)
            self.objects.pop(Key, None)

    class _FakeBody:
        def __init__(self, content: bytes):
            self.content = content

        def read(self) -> bytes:
            return self.content

    fake_client = FakeS3Client()
    monkeypatch.setattr(storage_service, "get_settings", lambda: settings)
    monkeypatch.setattr(storage_service, "_s3_client", lambda _settings: fake_client)

    key = storage_service.save_pdf(b"%PDF-remote")

    assert fake_client.upload_metadata == {
        "bucket": "deposit360-documents",
        "content_type": "application/pdf",
    }
    assert storage_service.read_file(key) == b"%PDF-remote"
    storage_service.delete_file(key)
    assert fake_client.deleted == [key]


def test_s3_storage_reports_missing_configuration(monkeypatch):
    settings = Settings(storage_backend="s3")
    monkeypatch.setattr(storage_service, "get_settings", lambda: settings)

    with pytest.raises(RuntimeError, match="S3 storage requires"):
        storage_service.save_pdf(b"%PDF")
