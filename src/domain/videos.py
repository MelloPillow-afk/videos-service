"""Videos managed through the admin API."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class VideoStatus(StrEnum):
    CREATED = "CREATED"
    UPLOADING = "UPLOADING"
    PROCESSING = "PROCESSING"
    READY = "READY"
    FAILED = "FAILED"


class PublicationStatus(StrEnum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"


@dataclass(frozen=True, slots=True)
class Video:
    id: UUID
    title: str
    description: str | None
    status: VideoStatus
    publication_status: PublicationStatus
    published_at: datetime | None
    created_at: datetime
    updated_at: datetime
    latest_job_id: UUID | None


class VideoNotFound(Exception):
    """No video exists with the requested ID, or it has been deleted."""


class VideoNotReady(Exception):
    """Only a ready video can be published."""
