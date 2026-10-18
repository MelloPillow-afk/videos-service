"""HTTP handlers for managing videos."""

from dataclasses import replace
from typing import Annotated
from uuid import UUID

from fastapi import HTTPException, Path, Query, Request, Response

from src.domain import videos as domain
from src.handlers.jobs import job_resource
from src.handlers.playback import playback_resource
from src.handlers.utilities import page, page_position, thumbnail, timestamp
from src.schemas.generated.jobs import Job
from src.schemas.generated.operations import (
    AdminVideosCompleteUploadIdParameter,
    AdminVideosDeleteVideoIdParameter,
    AdminVideosGetPlaybackIdParameter,
    AdminVideosGetVideoIdParameter,
    AdminVideosListVideosLimitParameter,
    AdminVideosListVideosPageTokenParameter,
    AdminVideosUpdateVideoIdParameter,
    AdminVideosUploadUrlIdParameter,
)
from src.schemas.generated.playback import Playback
from src.schemas.generated.uploads import (
    SourceUpload,
    SourceUploadCreate,
    Upload,
    UploadComplete,
    UploadHeaders,
)
from src.schemas.generated.videos import (
    AdminVideo,
    AdminVideoCreate,
    AdminVideos,
    AdminVideoUpdate,
    PublicationStatus,
)
from src.services import uploads as uploads_service
from src.services import videos as videos_service

_NOT_FOUND = "The video was not found."
_NOT_ELIGIBLE = "The video is not eligible for this operation."
_TOO_LARGE = "The file exceeds the configured size limit."


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
        raise HTTPException(status_code=404, detail=_NOT_FOUND) from None
    return _video(video)


async def get_playback(
    *,
    id: Annotated[AdminVideosGetPlaybackIdParameter, Path(alias="id", description="Video ID.")],
) -> Playback:
    try:
        video = await videos_service.get_previewable_video(UUID(id))
    except domain.VideoNotFound:
        raise HTTPException(status_code=404, detail=_NOT_FOUND) from None
    except domain.VideoNotReady:
        raise HTTPException(status_code=409, detail="The video is not ready.") from None
    return playback_resource(video)


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
        raise HTTPException(status_code=404, detail=_NOT_FOUND) from None
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
        raise HTTPException(status_code=404, detail=_NOT_FOUND) from None


async def upload_url(
    *,
    id: Annotated[AdminVideosUploadUrlIdParameter, Path(alias="id", description="Video ID.")],
    body: SourceUploadCreate,
    request: Request,
) -> SourceUpload:
    try:
        video, upload = await uploads_service.create_upload(
            UUID(id), body.content_type, body.size_bytes, request.app.state.settings
        )
    except domain.VideoNotFound:
        raise HTTPException(status_code=404, detail=_NOT_FOUND) from None
    except domain.UploadTooLarge:
        raise HTTPException(status_code=413, detail=_TOO_LARGE) from None
    except domain.UploadNotAllowed:
        raise HTTPException(status_code=409, detail=_NOT_ELIGIBLE) from None
    assert video.upload_id is not None  # Starting an upload sets it.
    return SourceUpload(
        video_id=str(video.id),
        status="UPLOADING",
        upload=Upload(
            upload_id=str(video.upload_id),
            method="PUT",
            url=upload.url,
            headers=UploadHeaders.model_validate({"Content-Type": body.content_type}),
            expires_at=timestamp(upload.expires_at),
        ),
    )


async def complete_upload(
    *,
    id: Annotated[AdminVideosCompleteUploadIdParameter, Path(alias="id", description="Video ID.")],
    body: UploadComplete,
    response: Response,
    request: Request,
) -> Job:
    try:
        job = await uploads_service.complete_upload(
            UUID(id), UUID(body.upload_id), request.app.state.settings
        )
    except domain.VideoNotFound:
        raise HTTPException(status_code=404, detail=_NOT_FOUND) from None
    except domain.UploadMissing:
        raise HTTPException(status_code=404, detail="The uploaded file was not found.") from None
    except domain.UploadTooLarge:
        raise HTTPException(status_code=413, detail=_TOO_LARGE) from None
    except domain.UploadNotAllowed:
        raise HTTPException(status_code=409, detail=_NOT_ELIGIBLE) from None
    except domain.UploadNotCurrent:
        raise HTTPException(
            status_code=409, detail="This upload attempt is no longer current."
        ) from None
    except domain.UploadSizeMismatch:
        raise HTTPException(
            status_code=409, detail="The uploaded file's size differs from the declared size."
        ) from None
    response.headers["Location"] = f"/v1/jobs/{job.id}"
    return job_resource(job)


def _video(video: domain.Video) -> AdminVideo:
    return AdminVideo(
        id=str(video.id),
        title=video.title,
        description=video.description,
        status=video.status.value,
        publication_status=video.publication_status.value,
        size_bytes=video.size_bytes,
        duration_seconds=video.duration_seconds,
        thumbnail=thumbnail(video),
        published_at=timestamp(video.published_at) if video.published_at else None,
        created_at=timestamp(video.created_at),
        updated_at=timestamp(video.updated_at),
        latest_job_id=str(video.latest_job_id) if video.latest_job_id else None,
    )
