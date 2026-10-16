"""Persisted video state shared by application operations and workers."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class UploadKind(StrEnum):
    SOURCE = "SOURCE"
    THUMBNAIL = "THUMBNAIL"


class JobKind(StrEnum):
    VIDEO = "VIDEO"
    THUMBNAIL = "THUMBNAIL"
    DELETION = "DELETION"


@dataclass
class VideoRecord:
    id: UUID
    title: str
    description: str | None
    status: str
    publication_status: str
    source_key: str | None
    source_validated: bool
    playback_key: str | None
    size_bytes: int | None
    duration_seconds: float | None
    width: int | None
    height: int | None
    generated_thumbnail_status: str
    generated_thumbnail_key: str | None
    custom_thumbnail_key: str | None
    processing_error_code: str | None
    processing_error_message: str | None
    published_at: datetime | None
    created_at: datetime
    updated_at: datetime


class VideoNotFound(Exception):
    pass


class VideoConflict(Exception):
    pass
