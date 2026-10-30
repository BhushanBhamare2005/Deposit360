import uuid
from pathlib import Path

from app.core.config import get_settings


def save_pdf(content: bytes) -> str:
    storage_root = Path(get_settings().storage_local_path).resolve()
    storage_root.mkdir(parents=True, exist_ok=True)
    key = f"{uuid.uuid4()}.pdf"
    (storage_root / key).write_bytes(content)
    return key


def delete_file(storage_key: str) -> None:
    storage_root = Path(get_settings().storage_local_path).resolve()
    target = (storage_root / storage_key).resolve()
    if target.parent != storage_root:
        raise ValueError("Invalid storage key")
    target.unlink(missing_ok=True)
