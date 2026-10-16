"""Source attempt and accepted-work values independent of HTTP schemas."""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal
from uuid import UUID


@dataclass(frozen=True)
class UploadAttempt:
    id: UUID
    video_id: UUID
    kind: str
    object_key: str
    declared_size_bytes: int
    content_type: str
    expires_at: datetime
    is_current: bool
    state: str
    accepted_at: datetime | None
    created_at: datetime


@dataclass(frozen=True)
class SourceAccepted:
    video_id: UUID
    status: str
    processing_job_id: UUID
    thumbnail_status: str


class UploadRejected(Exception):
    def __init__(self, reason: Literal["missing", "too_large", "invalid"], message: str) -> None:
        self.reason = reason
        self.message = message
        super().__init__(message)
