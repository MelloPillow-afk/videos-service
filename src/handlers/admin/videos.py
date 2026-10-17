"""HTTP handlers for managing videos."""

from dataclasses import replace
from typing import Annotated
from uuid import UUID

from fastapi import HTTPException, Path, Query, Response

from src.domain import videos as domain
from src.handlers.utilities import page, page_position, timestamp
from src.schemas.generated.operations import (
    AdminVideosDeleteVideoIdParameter,
    AdminVideosGetVideoIdParameter,
    AdminVideosListVideosLimitParameter,
    AdminVideosListVideosPageTokenParameter,
    AdminVideosUpdateVideoIdParameter,
)
from src.schemas.generated.thumbnails import ThumbnailImage
from src.schemas.generated.videos import (
    AdminVideo,
    AdminVideoCreate,
    AdminVideos,
    AdminVideoUpdate,
    PublicationStatus,
)
from src.services import videos as videos_service


async def list_videos(
    *,
    limit: Annotated[
        AdminVideosListVideosLimitParameter,
        Query(alias="limit", description="Maximum number of videos to return."),
    ] = 20,
    page_token: Annotated[
        AdminVideosListVideosPageTokenParameter | None,
        Query(alias="page_token", description="The next_page_token from the previous page."),
    ] = None,
    publication_status: Annotated[
        PublicationStatus | None,
        Query(alias="publication_status", description="Filter by publication status."),
    ] = None,
) -> AdminVideos:
    videos = await videos_service.list_videos(
        domain.PublicationStatus(publication_status) if publication_status else None,
        page_position(page_token),
        limit + 1,
    )
    videos, pagination = page(videos, limit, lambda video: (video.created_at, video.id))
    return AdminVideos(data=[_video(video) for video in videos], pagination=pagination)


async def create_video(*, body: AdminVideoCreate, response: Response) -> AdminVideo:
    video = await videos_service.create_video(body.title, body.description)
    response.headers["Location"] = f"/v1/admin/videos/{video.id}"
    return _video(video)


async def get_video(
    *,
    id: Annotated[AdminVideosGetVideoIdParameter, Path(alias="id", description="Video ID.")],
) -> AdminVideo:
    try:
        video = await videos_service.get_video(UUID(id))
    except domain.VideoNotFound:
        raise HTTPException(status_code=404, detail="The video was not found.") from None
    return _video(video)


async def update_video(
    *,
    id: Annotated[AdminVideosUpdateVideoIdParameter, Path(alias="id", description="Video ID.")],
    body: AdminVideoUpdate,
) -> AdminVideo:
    # Only supplied fields change; unknown fields are ignored.
    supplied = body.model_fields_set
    try:
        video = await videos_service.get_video(UUID(id))
        video = await videos_service.update_video(
            replace(
                video,
                title=body.title if "title" in supplied else video.title,
                description=body.description if "description" in supplied else video.description,
                publication_status=domain.PublicationStatus(body.publication_status)
                if "publication_status" in supplied
                else video.publication_status,
            )
        )
    except domain.VideoNotFound:
        raise HTTPException(status_code=404, detail="The video was not found.") from None
    except domain.VideoNotReady:
        raise HTTPException(status_code=409, detail="The video is not ready.") from None
    return _video(video)


async def delete_video(
    *,
    id: Annotated[AdminVideosDeleteVideoIdParameter, Path(alias="id", description="Video ID.")],
) -> None:
    try:
        await videos_service.delete_video(UUID(id))
    except domain.VideoNotFound:
        raise HTTPException(status_code=404, detail="The video was not found.") from None


def _video(video: domain.Video) -> AdminVideo:
    # Size, duration, and thumbnail come from uploads and processing, which come later.
    return AdminVideo(
        id=str(video.id),
        title=video.title,
        description=video.description,
        status=video.status.value,
        publication_status=video.publication_status.value,
        size_bytes=None,
        duration_seconds=None,
        thumbnail=ThumbnailImage(status="PENDING", source="NONE", url=None),
        published_at=timestamp(video.published_at) if video.published_at else None,
        created_at=timestamp(video.created_at),
        updated_at=timestamp(video.updated_at),
        latest_job_id=str(video.latest_job_id) if video.latest_job_id else None,
    )
