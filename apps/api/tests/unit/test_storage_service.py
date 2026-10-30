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


def test_vercel_blob_storage_saves_reads_and_deletes_pdf(monkeypatch):
    settings = Settings(
        storage_backend="vercel_blob",
    )

    class FakeVercelBlob:
        def __init__(self):
            self.objects: dict[str, bytes] = {}
            self.upload_metadata: dict[str, str] = {}
            self.deleted: list[str] = []

        def put_blob(self, key: str, body: bytes, *, access: str, content_type: str):
            self.objects[key] = body
            self.upload_metadata = {"access": access, "content_type": content_type}

        def get_blob(self, key: str, *, access: str):
            assert access == "private"
            return _FakeBlobResult(self.objects[key])

        def delete_blob(self, key: str):
            self.deleted.append(key)
            self.objects.pop(key, None)

    class _FakeBlobResult:
        def __init__(self, content: bytes):
            self.body = content

    fake_blob = FakeVercelBlob()
    monkeypatch.setattr(storage_service, "get_settings", lambda: settings)
    monkeypatch.setattr(storage_service, "blob_sync", fake_blob)

    key = storage_service.save_pdf(b"%PDF-vercel")

    assert fake_blob.upload_metadata == {
        "access": "private",
        "content_type": "application/pdf",
    }
    assert storage_service.read_file(key) == b"%PDF-vercel"
    storage_service.delete_file(key)
    assert fake_blob.deleted == [key]
