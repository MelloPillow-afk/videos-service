"""Controlled object provider with atomic create-once semantics."""

import asyncio
from urllib.parse import unquote, urlsplit

from src.providers.storage import (
    StorageArea,
    StorageConflictError,
    StorageLimitError,
    StorageMissingError,
    StoredObject,
    UploadInstructions,
)


class MemoryStorage:
    def __init__(self) -> None:
        self.head_started: asyncio.Event | None = None
        self.head_release: asyncio.Event | None = None
        self.size_overrides: dict[str, int] = {}
        self.objects: dict[tuple[StorageArea, str], tuple[bytes, str]] = {}

    async def head(self, area: StorageArea, key: str) -> StoredObject | None:
        if self.head_started is not None and self.head_release is not None:
            self.head_started.set()
            await self.head_release.wait()
        item = self.objects.get((area, key))
        if item is not None and key in self.size_overrides:
            return StoredObject(self.size_overrides[key], item[1])
        return StoredObject(len(item[0]), item[1]) if item is not None else None

    async def read(self, area: StorageArea, key: str, max_bytes: int) -> bytes:
        item = self.objects.get((area, key))
        if item is None:
            raise StorageMissingError
        if len(item[0]) > max_bytes:
            raise StorageLimitError
        return item[0]

    async def write(
        self,
        area: StorageArea,
        key: str,
        data: bytes,
        content_type: str,
        *,
        create_only: bool = True,
    ) -> None:
        if create_only and (area, key) in self.objects:
            raise StorageConflictError
        self.objects[area, key] = data, content_type

    async def list(self, area: StorageArea, prefix: str) -> list[str]:
        return [
            key
            for (stored_area, key) in self.objects
            if stored_area == area and key.startswith(prefix)
        ]

    async def delete(self, area: StorageArea, key: str) -> None:
        self.objects.pop((area, key), None)

    async def sign_upload(
        self, key: str, content_type: str, expires_seconds: int = 900
    ) -> UploadInstructions:
        return UploadInstructions(
            "https://uploads.test/" + key + "?signature=controlled",
            {"Content-Type": content_type, "If-None-Match": "*"},
        )

    async def browser_put(self, url: str, data: bytes, headers: dict[str, str]) -> None:
        assert headers["If-None-Match"] == "*"
        await self.write(
            "private", unquote(urlsplit(url).path.lstrip("/")), data, headers["Content-Type"]
        )
