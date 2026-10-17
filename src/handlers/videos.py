"""HTTP handlers for the public video catalog."""

from datetime import datetime
from typing import Annotated

from fastapi import Query

from src.domain import videos as domain
from src.handlers.utilities import page, page_position, timestamp
from src.schemas.generated.operations import (
    VideosListVideosLimitParameter,
    VideosListVideosPageTokenParameter,
)
from src.schemas.generated.thumbnails import ThumbnailImage
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


def _video(video: domain.Video) -> Video:
    # Duration and thumbnail come from processing, which comes later.
    return Video(
        id=str(video.id),
        title=video.title,
        description=video.description,
        duration_seconds=None,
        thumbnail=ThumbnailImage(status="PENDING", source="NONE", url=None),
        published_at=timestamp(_published_at(video)),
    )


def _published_at(video: domain.Video) -> datetime:
    # The catalog lists only published videos, and every published video has a time.
    assert video.published_at is not None
    return video.published_at
