"""HTTP handlers for managing videos."""

from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import HTTPException, Path, Response

from src.domain import videos as domain
from src.schemas.generated.operations import AdminVideosGetVideoIdParameter
from src.schemas.generated.thumbnails import ThumbnailImage
from src.schemas.generated.videos import Video, VideoCreate
from src.services import videos as videos_service


async def create_video(*, body: VideoCreate, response: Response) -> Video:
    video = await videos_service.create_video(body.title, body.description)
    response.headers["Location"] = f"/v1/admin/videos/{video.id}"
    return _video(video)


async def get_video(
    *,
    id: Annotated[AdminVideosGetVideoIdParameter, Path(alias="id", description="Video ID.")],
) -> Video:
    try:
        video = await videos_service.get_video(UUID(id))
    except domain.VideoNotFound:
        raise HTTPException(status_code=404, detail="The video was not found.") from None
    return _video(video)


def _video(video: domain.Video) -> Video:
    # Size, duration, and thumbnail come from uploads and processing, which come later.
    return Video(
        id=str(video.id),
        title=video.title,
        description=video.description,
        status=video.status.value,
        publication_status=video.publication_status.value,
        size_bytes=None,
        duration_seconds=None,
        thumbnail=ThumbnailImage(status="PENDING", source="NONE", url=None),
        published_at=_timestamp(video.published_at) if video.published_at else None,
        created_at=_timestamp(video.created_at),
        updated_at=_timestamp(video.updated_at),
        latest_job_id=str(video.latest_job_id) if video.latest_job_id else None,
    )


def _timestamp(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")
