"""Business rules for managing videos."""

from dataclasses import replace
from datetime import UTC, datetime
from uuid import UUID

from src.domain.videos import (
    PublicationStatus,
    Video,
    VideoNotFound,
    VideoNotReady,
    VideoStatus,
)
from src.repositories import videos as videos_repository


async def create_video(title: str, description: str | None) -> Video:
    return await videos_repository.create_video(title, description)


async def get_video(video_id: UUID) -> Video:
    video = await videos_repository.get_video(video_id)
    if video is None:
        raise VideoNotFound(video_id)
    return video


async def update_video(video: Video) -> Video:
    """Save an edited video, keeping its publication time consistent with its status."""
    if video.publication_status is PublicationStatus.PUBLISHED:
        if video.status is not VideoStatus.READY:
            raise VideoNotReady(video.id)
        # Publishing again keeps the original publication time.
        video = replace(video, published_at=video.published_at or datetime.now(UTC))
    else:
        video = replace(video, published_at=None)
    updated = await videos_repository.update_video(video)
    if updated is None:
        raise VideoNotFound(video.id)  # Deleted after it was read.
    return updated
