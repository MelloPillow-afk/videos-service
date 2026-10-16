"""Read-only cleanup inventory and retained writer history."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class UploadWriter:
    id: UUID
    kind: str
    state: str
    object_key: str
    public_object_key: str | None
    expires_at: datetime


@dataclass(frozen=True)
class WorkerWriter:
    id: UUID
    kind: str
    state: str
    execution_attempts: int
    execution_reference: str | None
    output_prefix: str
    output_keys: list[str]


@dataclass(frozen=True)
class CleanupInventory:
    job_id: UUID
    video_id: UUID
    private_keys: tuple[str, ...]
    public_keys: tuple[str, ...]
    prefixes: tuple[str, ...]
    uploads: tuple[UploadWriter, ...]
    workers: tuple[WorkerWriter, ...]
    storage_listed: bool = False
    physical_cleanup_complete: bool = False
