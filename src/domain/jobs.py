"""Background work tracked for a video."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class JobKind(StrEnum):
    VIDEO_PROCESSING = "VIDEO_PROCESSING"
    THUMBNAIL_GENERATION = "THUMBNAIL_GENERATION"
    CUSTOM_THUMBNAIL_PROCESSING = "CUSTOM_THUMBNAIL_PROCESSING"
    DELETION = "DELETION"


class JobStatus(StrEnum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"


@dataclass(frozen=True, slots=True)
class Job:
    id: UUID
    video_id: UUID
    kind: JobKind
    status: JobStatus
    message: str | None
    created_at: datetime
    updated_at: datetime


class JobNotFound(Exception):
    """No job exists with the requested ID."""
