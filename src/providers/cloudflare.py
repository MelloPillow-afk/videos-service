"""Cloudflare R2 object storage, through its S3-compatible API."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from src.config import Settings

# Stubs are a development dependency.
if TYPE_CHECKING:
    from mypy_boto3_s3 import S3Client


@dataclass(frozen=True, slots=True)
class PresignedUpload:
    url: str
    expires_at: datetime


_client: S3Client | None = None
_settings: Settings | None = None


def open_storage(settings: Settings) -> None:
    """Create the process-wide R2 client; the application lifespan calls this on startup."""
    global _client, _settings
    # The stubs type only S3; boto3's overloads for other services are unknown.
    _client = boto3.client(  # pyright: ignore[reportUnknownMemberType]
        "s3",
        endpoint_url=settings.r2_endpoint_url,
        aws_access_key_id=settings.r2_access_key_id.get_secret_value(),
        aws_secret_access_key=settings.r2_secret_access_key.get_secret_value(),
        region_name="auto",
        config=Config(signature_version="s3v4"),
    )
    _settings = settings


def close_storage() -> None:
    global _client, _settings
    _client, _settings = None, None


def presign_upload(key: str, content_type: str) -> PresignedUpload:
    """A URL that lets a client PUT one file into the private upload bucket."""
    client, settings = _storage()
    expires_at = datetime.now(UTC) + timedelta(seconds=settings.upload_url_ttl_seconds)
    # Signing is local; it makes no request to R2.
    url = client.generate_presigned_url(
        "put_object",
        Params={"Bucket": settings.r2_raw_bucket, "Key": key, "ContentType": content_type},
        ExpiresIn=settings.upload_url_ttl_seconds,
    )
    return PresignedUpload(url=url, expires_at=expires_at)


async def uploaded_size(key: str) -> int | None:
    """The size of an uploaded file, or None when nothing was uploaded at the key."""
    client, settings = _storage()
    try:
        head = await asyncio.to_thread(client.head_object, Bucket=settings.r2_raw_bucket, Key=key)
    except ClientError as error:
        if error.response.get("Error", {}).get("Code") in ("404", "NoSuchKey", "NotFound"):
            return None
        raise
    return head["ContentLength"]


async def download_source(key: str, path: Path) -> None:
    """Save an uploaded file from the private upload bucket to a local path."""
    client, settings = _storage()
    await asyncio.to_thread(client.download_file, settings.r2_raw_bucket, key, str(path))


async def upload_media(path: Path, key: str) -> None:
    """Publish a processed file to the public media bucket."""
    client, settings = _storage()
    await asyncio.to_thread(
        client.upload_file,
        str(path),
        settings.r2_processed_bucket,
        key,
        ExtraArgs={"ContentType": _MEDIA_TYPES[path.suffix]},
    )


_MEDIA_TYPES = {
    ".m3u8": "application/vnd.apple.mpegurl",
    ".ts": "video/mp2t",
    ".jpg": "image/jpeg",
}


def media_url(key: str) -> str:
    """Where viewers fetch a processed file from the public media bucket."""
    _, settings = _storage()
    return f"{settings.media_base_url.rstrip('/')}/{key}"


def _storage() -> tuple[S3Client, Settings]:
    if _client is None or _settings is None:
        raise RuntimeError("Storage is not open; it opens in the application lifespan")
    return _client, _settings
