"""Videos managed through the admin API."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from src.domain.jobs import JobStatus


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
    # The current upload; a new upload URL replaces it.
    upload_id: UUID | None
    source_key: str | None
    size_bytes: int | None
    # Set by processing.
    duration_seconds: float | None
    playback_key: str | None
    # Where the generated thumbnail's sizes are stored.
    generated_thumbnail_prefix: str | None
    thumbnail_job_status: JobStatus | None
    # The current custom thumbnail upload; a new upload URL replaces it.
    thumbnail_upload_id: UUID | None
    thumbnail_upload_key: str | None
    thumbnail_upload_size_bytes: int | None
    # Set once the custom thumbnail's sizes are rendered; shown instead of the generated one.
    custom_thumbnail_prefix: str | None


class VideoNotFound(Exception):
    """No video exists with the requested ID, or it has been deleted."""


class VideoNotReady(Exception):
    """Only a ready video can be published or played."""


class UploadNotAllowed(Exception):
    """The video's status does not allow this upload step."""


class UploadNotCurrent(Exception):
    """The upload ID is not the video's current upload."""


class UploadTooLarge(Exception):
    """The file exceeds the configured size limit."""


class UploadMissing(Exception):
    """No file was uploaded for the current upload."""


class UploadSizeMismatch(Exception):
    """The uploaded file's size differs from the size declared for the upload."""


class InvalidMedia(Exception):
    """The uploaded file is not a video the service accepts; the message says why."""


class VideoChanged(Exception):
    """The video was deleted or its job finished while a worker processed it."""
