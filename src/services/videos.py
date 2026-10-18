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


async def get_playable_video(video_id: UUID) -> Video:
    """A published video whose processed media viewers can play."""
    video = await get_video(video_id)
    if video.publication_status is not PublicationStatus.PUBLISHED:
        raise VideoNotFound(video_id)
    return _ready(video)


async def get_previewable_video(video_id: UUID) -> Video:
    """A video with processed media admins can play, published or not."""
    return _ready(await get_video(video_id))


def _ready(video: Video) -> Video:
    if video.status is not VideoStatus.READY or video.playback_key is None:
        raise VideoNotReady(video.id)
    return video


async def get_catalog_video(video_id: UUID) -> Video:
    """A video the catalog lists: published, ready, and not deleted."""
    video = await get_video(video_id)
    if (
        video.publication_status is not PublicationStatus.PUBLISHED
        or video.status is not VideoStatus.READY
    ):
        raise VideoNotFound(video_id)
    return video


async def list_videos(
    publication_status: PublicationStatus | None,
    after: tuple[datetime, UUID] | None,
    limit: int,
) -> list[Video]:
    return await videos_repository.list_videos(publication_status, after, limit)


async def list_catalog_videos(after: tuple[datetime, UUID] | None, limit: int) -> list[Video]:
    return await videos_repository.list_catalog_videos(after, limit)


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
        raise VideoNotFound(video.id)
    return updated


async def delete_video(video_id: UUID) -> None:
    if not await videos_repository.delete_video(video_id):
        raise VideoNotFound(video_id)
