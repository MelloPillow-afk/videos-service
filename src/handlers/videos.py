"""HTTP handlers for the public video catalog."""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import HTTPException, Path, Query

from src.domain import videos as domain
from src.handlers.utilities import page, page_position, thumbnail, timestamp
from src.schemas.generated.operations import (
    VideosGetVideoIdParameter,
    VideosListVideosLimitParameter,
    VideosListVideosPageTokenParameter,
)
from src.schemas.generated.videos import Video, Videos
from src.services import videos as videos_service


async def list_videos(
    *,
    limit: Annotated[
        VideosListVideosLimitParameter,
        Query(alias="limit", description="Maximum number of videos to return."),
    ] = 20,
    page_token: Annotated[
        VideosListVideosPageTokenParameter | None,
        Query(alias="page_token", description="The next_page_token from the previous page."),
    ] = None,
) -> Videos:
    videos = await videos_service.list_catalog_videos(page_position(page_token), limit + 1)
    videos, pagination = page(videos, limit, lambda video: (_published_at(video), video.id))
    return Videos(data=[_video(video) for video in videos], pagination=pagination)


async def get_video(
    *,
    id: Annotated[VideosGetVideoIdParameter, Path(alias="id", description="Video ID.")],
) -> Video:
    try:
        video = await videos_service.get_catalog_video(UUID(id))
    except domain.VideoNotFound:
        raise HTTPException(status_code=404, detail="The video was not found.") from None
    return _video(video)


def _video(video: domain.Video) -> Video:
    return Video(
        id=str(video.id),
        title=video.title,
        description=video.description,
        duration_seconds=video.duration_seconds,
        thumbnail=thumbnail(video),
        published_at=timestamp(_published_at(video)),
    )


def _published_at(video: domain.Video) -> datetime:
    # The catalog shows only published videos, and every published video has a time.
    assert video.published_at is not None
    return video.published_at
