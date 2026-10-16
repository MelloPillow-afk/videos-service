"""Object-storage boundary; ordinary writers only create immutable objects."""

from dataclasses import dataclass
from typing import Literal, Protocol

StorageArea = Literal["private", "public"]


@dataclass(frozen=True)
class StoredObject:
    size_bytes: int
    content_type: str


@dataclass(frozen=True)
class UploadInstructions:
    url: str
    headers: dict[str, str]
    method: str = "PUT"


class TemporaryStorageError(Exception):
    pass


class StorageConflictError(Exception):
    pass


class StorageMissingError(Exception):
    pass


class StorageLimitError(Exception):
    pass


class Storage(Protocol):
    async def head(self, area: StorageArea, key: str) -> StoredObject | None: ...
    async def read(self, area: StorageArea, key: str, max_bytes: int) -> bytes: ...
    async def write(self, area: StorageArea, key: str, data: bytes, content_type: str,
                    *, create_only: bool = True) -> None: ...
    async def list(self, area: StorageArea, prefix: str) -> list[str]: ...
    async def delete(self, area: StorageArea, key: str) -> None: ...
    async def sign_upload(self, key: str, content_type: str,
                          expires_seconds: int = 900) -> UploadInstructions: ...
