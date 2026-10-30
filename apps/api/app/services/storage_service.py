import uuid
from pathlib import Path

import boto3
from botocore.exceptions import ClientError

from app.core.config import Settings, get_settings


def _validate_key(storage_key: str) -> None:
    if not storage_key or Path(storage_key).name != storage_key:
        raise ValueError("Invalid storage key")


def _s3_client(settings: Settings):
    required = (
        settings.storage_s3_endpoint_url,
        settings.storage_s3_bucket,
        settings.storage_s3_access_key_id,
        settings.storage_s3_secret_access_key,
    )
    if not all(required):
        raise RuntimeError("S3 storage requires an endpoint, bucket, access key, and secret key")
    return boto3.client(
        "s3",
        endpoint_url=settings.storage_s3_endpoint_url,
        aws_access_key_id=settings.storage_s3_access_key_id,
        aws_secret_access_key=settings.storage_s3_secret_access_key,
        region_name=settings.storage_s3_region,
    )


def save_pdf(content: bytes) -> str:
    settings = get_settings()
    key = f"{uuid.uuid4()}.pdf"
    if settings.storage_backend == "s3":
        _s3_client(settings).put_object(
            Bucket=settings.storage_s3_bucket,
            Key=key,
            Body=content,
            ContentType="application/pdf",
        )
    else:
        storage_root = Path(settings.storage_local_path).resolve()
        storage_root.mkdir(parents=True, exist_ok=True)
        (storage_root / key).write_bytes(content)
    return key


def read_file(storage_key: str) -> bytes:
    _validate_key(storage_key)
    settings = get_settings()
    if settings.storage_backend == "s3":
        try:
            result = _s3_client(settings).get_object(
                Bucket=settings.storage_s3_bucket,
                Key=storage_key,
            )
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") in {"404", "NoSuchKey", "NotFound"}:
                raise FileNotFoundError("Stored document not found") from exc
            raise
        return result["Body"].read()
    storage_root = Path(settings.storage_local_path).resolve()
    target = (storage_root / storage_key).resolve()
    if target.parent != storage_root or not target.is_file():
        raise FileNotFoundError("Stored document not found")
    return target.read_bytes()


def delete_file(storage_key: str) -> None:
    _validate_key(storage_key)
    settings = get_settings()
    if settings.storage_backend == "s3":
        _s3_client(settings).delete_object(
            Bucket=settings.storage_s3_bucket,
            Key=storage_key,
        )
        return
    storage_root = Path(settings.storage_local_path).resolve()
    target = (storage_root / storage_key).resolve()
    if target.parent != storage_root:
        raise ValueError("Invalid storage key")
    target.unlink(missing_ok=True)
