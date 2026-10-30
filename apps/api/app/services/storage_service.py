import uuid
from pathlib import Path

from vercel import blob
from vercel.blob import sync as blob_sync

from app.core.config import get_settings


def _validate_key(storage_key: str) -> None:
    if not storage_key or Path(storage_key).name != storage_key:
        raise ValueError("Invalid storage key")


def save_pdf(content: bytes) -> str:
    settings = get_settings()
    key = f"{uuid.uuid4()}.pdf"
    if settings.storage_backend == "vercel_blob":
        blob_sync.put_blob(
            key,
            content,
            access="private",
            content_type="application/pdf",
        )
    else:
        storage_root = Path(settings.storage_local_path).resolve()
        storage_root.mkdir(parents=True, exist_ok=True)
        (storage_root / key).write_bytes(content)
    return key


def read_file(storage_key: str) -> bytes:
    _validate_key(storage_key)
    settings = get_settings()
    if settings.storage_backend == "vercel_blob":
        try:
            return blob_sync.get_blob(storage_key, access="private").body
        except blob.BlobNotFoundError as exc:
            raise FileNotFoundError("Stored document not found") from exc
    storage_root = Path(settings.storage_local_path).resolve()
    target = (storage_root / storage_key).resolve()
    if target.parent != storage_root or not target.is_file():
        raise FileNotFoundError("Stored document not found")
    return target.read_bytes()


def delete_file(storage_key: str) -> None:
    _validate_key(storage_key)
    settings = get_settings()
    if settings.storage_backend == "vercel_blob":
        blob_sync.delete_blob(storage_key)
        return
    storage_root = Path(settings.storage_local_path).resolve()
    target = (storage_root / storage_key).resolve()
    if target.parent != storage_root:
        raise ValueError("Invalid storage key")
    target.unlink(missing_ok=True)
