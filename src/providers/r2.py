"""R2 S3 adapter with signed conditional browser uploads and bounded reads."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import TYPE_CHECKING, TypeVar

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

from src.config import Settings
from src.providers.storage import (
    StorageArea,
    StorageConflictError,
    StorageLimitError,
    StorageMissingError,
    StoredObject,
    TemporaryStorageError,
    UploadInstructions,
)

if TYPE_CHECKING:
    from mypy_boto3_s3 import S3Client
    from mypy_boto3_s3.type_defs import ListObjectsV2RequestTypeDef

T = TypeVar("T")


class R2Storage:
    def __init__(self, settings: Settings, *, client: S3Client | None = None) -> None:
        self.settings = settings
        self._client = client
        if client is None and all(
            (settings.r2_endpoint_url, settings.r2_access_key_id, settings.r2_secret_access_key)
        ):
            assert settings.r2_access_key_id and settings.r2_secret_access_key
            self._client = boto3.client(  # pyright: ignore[reportUnknownMemberType]
                "s3",
                endpoint_url=settings.r2_endpoint_url,
                region_name="auto",
                aws_access_key_id=settings.r2_access_key_id.get_secret_value(),
                aws_secret_access_key=settings.r2_secret_access_key.get_secret_value(),
                config=Config(
                    signature_version="s3v4",
                    connect_timeout=5,
                    read_timeout=30,
                    retries={"total_max_attempts": 3, "mode": "standard"},
                    s3={"addressing_style": "path"},
                ),
            )

    @property
    def client(self) -> S3Client:
        if self._client is None:
            raise TemporaryStorageError("Object storage is unavailable.")
        return self._client

    def bucket(self, area: StorageArea) -> str:
        bucket = (
            self.settings.r2_private_bucket if area == "private" else self.settings.r2_public_bucket
        )
        if not bucket:
            raise TemporaryStorageError("Object storage is unavailable.")
        return bucket

    async def _run(self, function: Callable[[], T]) -> T:
        try:
            return await asyncio.to_thread(function)
        except ClientError as error:
            code = error.response.get("Error", {}).get("Code", "")
            if code in ("NoSuchKey", "NotFound", "404"):
                raise StorageMissingError from None
            if code in ("PreconditionFailed", "412", "ConditionalRequestConflict"):
                raise StorageConflictError from None
            raise TemporaryStorageError("Object storage request failed.") from None
        except (BotoCoreError, OSError):
            raise TemporaryStorageError("Object storage request failed.") from None

    async def sign_upload(
        self, key: str, content_type: str, expires_seconds: int = 900
    ) -> UploadInstructions:
        url = await self._run(
            lambda: self.client.generate_presigned_url(
                "put_object",
                Params={
                    "Bucket": self.bucket("private"),
                    "Key": key,
                    "ContentType": content_type,
                    "IfNoneMatch": "*",
                },
                ExpiresIn=expires_seconds,
                HttpMethod="PUT",
            )
        )
        return UploadInstructions(url, {"Content-Type": content_type, "If-None-Match": "*"})

    async def head(self, area: StorageArea, key: str) -> StoredObject | None:
        try:
            result = await self._run(
                lambda: self.client.head_object(Bucket=self.bucket(area), Key=key)
            )
            return StoredObject(
                result["ContentLength"], result.get("ContentType", "application/octet-stream")
            )
        except StorageMissingError:
            return None

    async def read(self, area: StorageArea, key: str, max_bytes: int) -> bytes:
        def download() -> bytes:
            result = self.client.get_object(Bucket=self.bucket(area), Key=key)
            stream = result["Body"]
            try:
                if result.get("ContentLength", 0) > max_bytes:
                    raise StorageLimitError
                data = stream.read(max_bytes + 1)
                if len(data) > max_bytes:
                    raise StorageLimitError
                return data
            finally:
                stream.close()

        return await self._run(download)

    async def write(
        self,
        area: StorageArea,
        key: str,
        data: bytes,
        content_type: str,
        *,
        create_only: bool = True,
    ) -> None:
        if not create_only:
            raise ValueError("Ordinary object writers must use create-only PUTs.")
        await self._run(
            lambda: self.client.put_object(
                Bucket=self.bucket(area),
                Key=key,
                Body=data,
                ContentType=content_type,
                IfNoneMatch="*",
            )
        )

    async def list(self, area: StorageArea, prefix: str) -> list[str]:
        keys: list[str] = []
        token = ""
        while True:
            parameters: ListObjectsV2RequestTypeDef = {
                "Bucket": self.bucket(area),
                "Prefix": prefix,
            }
            if token:
                parameters["ContinuationToken"] = token
            response = await self._run(
                lambda parameters=parameters: self.client.list_objects_v2(**parameters)
            )
            keys.extend(item["Key"] for item in response.get("Contents", []) if "Key" in item)
            if not response.get("IsTruncated"):
                return keys
            token = response["NextContinuationToken"]

    async def delete(self, area: StorageArea, key: str) -> None:
        await self._run(lambda: self.client.delete_object(Bucket=self.bucket(area), Key=key))
