"""HTTP adapters for persisted video operations."""

from uuid import UUID

from fastapi import HTTPException, Request, Response

from src.domain.library import InvalidCursor, LibraryQuery
from src.domain.uploads import UploadRejected
from src.domain.videos import VideoConflict, VideoNotFound
from src.handlers.dependencies import optional_admin, require_admin
from src.handlers.video_projection import video_response
from src.providers.storage import TemporaryStorageError
from src.schemas.generated.operations import (
    VideosCompleteUploadIdParameter,
    VideosDeleteVideoIdParameter,
    VideosGetVideoIdParameter,
    VideosListVideosCursorParameter,
    VideosListVideosLimitParameter,
    VideosListVideosSearchParameter,
    VideosRetryProcessingIdParameter,
    VideosUpdateVideoIdParameter,
    VideosUploadUrlIdParameter,
)
from src.schemas.generated.uploads import (
    SourceUpload,
    SourceUploadCreate,
    SourceUploadProcessing,
    UploadComplete,
)
from src.schemas.generated.videos import (
    PublicationStatus,
    Video,
    VideoCreate,
    VideoDeletion,
    VideoRetry,
    Videos,
    VideoStatus,
    VideoUpdate,
)
from src.services.deletion import Deletions
from src.services.library import LibraryService
from src.services.processing_recovery import ProcessingRecovery
from src.services.uploads import SourceUploads
from src.services.videos import VideoService


async def create_video(*, body: VideoCreate, response: Response, request: Request) -> Video:
    await require_admin(request)
    service: VideoService = request.app.state.videos
    video = await service.create(body.title, body.description)
    response.headers["Location"] = f"/v1/videos/{video.id}"
    return video_response(video, request.app.state.settings.cdn_origin)


async def get_video(*, id: VideosGetVideoIdParameter, request: Request) -> Video:
    service: VideoService = request.app.state.videos
    try:
        return video_response(
            await service.get(UUID(id), administrator=await optional_admin(request)),
            request.app.state.settings.cdn_origin,
        )
    except VideoNotFound:
        raise HTTPException(404, "The video was not found.") from None


async def update_video(
    *, id: VideosUpdateVideoIdParameter, body: VideoUpdate, request: Request
) -> Video:
    await require_admin(request)
    service: VideoService = request.app.state.videos
    try:
        return video_response(
            await service.update(UUID(id), body.model_dump(exclude_unset=True)),
            request.app.state.settings.cdn_origin,
        )
    except VideoNotFound:
        raise HTTPException(404, "The video was not found.") from None
    except VideoConflict as error:
        raise HTTPException(409, str(error)) from None


async def list_videos(
    *,
    request: Request,
    cursor: VideosListVideosCursorParameter | None = None,
    limit: VideosListVideosLimitParameter = 20,
    publication_status: PublicationStatus | None = None,
    search: VideosListVideosSearchParameter | None = None,
    status: VideoStatus | None = None,
) -> Videos:
    administrator = await optional_admin(request)
    if not administrator and (status is not None or publication_status is not None):
        raise HTTPException(403, "Administrator access is required for these filters.")
    service = LibraryService(request.app.state.database)
    try:
        videos, token = await service.list(
            query=LibraryQuery(administrator, status, publication_status, search, limit),
            cursor=cursor,
        )
    except InvalidCursor:
        raise HTTPException(400, "The cursor is invalid for this query.") from None
    return Videos.model_validate(
        {
            "data": [
                video_response(video, request.app.state.settings.cdn_origin).model_dump(
                    exclude_unset=True
                )
                for video in videos
            ],
            "pagination": {"has_more": token is not None, "next_page_token": token},
        }
    )


async def delete_video(*, id: VideosDeleteVideoIdParameter, request: Request) -> VideoDeletion:
    await require_admin(request)
    service: Deletions = request.app.state.deletions
    try:
        await service.request(UUID(id))
    except VideoNotFound:
        raise HTTPException(404, "The video was not found.") from None
    return VideoDeletion(video_id=id, status="DELETING")


async def upload_url(
    *, id: VideosUploadUrlIdParameter, body: SourceUploadCreate, request: Request
) -> SourceUpload:
    await require_admin(request)
    service: SourceUploads = request.app.state.uploads
    try:
        result = await service.issue(UUID(id), body.content_type, body.size_bytes)
    except VideoNotFound:
        raise HTTPException(404, "The video was not found.") from None
    except VideoConflict as error:
        raise HTTPException(409, str(error)) from None
    except UploadRejected as error:
        raise HTTPException(
            {"missing": 404, "too_large": 413, "invalid": 400}[error.reason], error.message
        ) from None
    except TemporaryStorageError:
        raise HTTPException(503, "Object storage is temporarily unavailable.") from None
    return SourceUpload.model_validate(
        {
            "video_id": id,
            "status": "UPLOADING",
            "upload": {
                "upload_id": str(result.attempt.id),
                "method": result.upload.method,
                "url": result.upload.url,
                "headers": result.upload.headers,
                "expires_at": result.attempt.expires_at.isoformat().replace("+00:00", "Z"),
            },
        }
    )


async def complete_upload(
    *, id: VideosCompleteUploadIdParameter, body: UploadComplete, request: Request
) -> SourceUploadProcessing:
    await require_admin(request)
    service: SourceUploads = request.app.state.uploads
    try:
        result = await service.confirm(UUID(id), UUID(body.upload_id))
    except VideoNotFound:
        raise HTTPException(404, "The video was not found.") from None
    except VideoConflict as error:
        raise HTTPException(409, str(error)) from None
    except UploadRejected as error:
        raise HTTPException(
            {"missing": 404, "too_large": 413, "invalid": 400}[error.reason], error.message
        ) from None
    except TemporaryStorageError:
        raise HTTPException(503, "Object storage is temporarily unavailable.") from None
    return SourceUploadProcessing.model_validate(
        {
            "video_id": str(result.video_id),
            "status": result.status,
            "processing_job_id": str(result.processing_job_id),
            "thumbnail_status": result.thumbnail_status,
        }
    )


async def retry_processing(*, id: VideosRetryProcessingIdParameter, request: Request) -> VideoRetry:
    await require_admin(request)
    service: ProcessingRecovery = request.app.state.processing_recovery
    try:
        result = await service.retry(UUID(id))
    except VideoNotFound:
        raise HTTPException(404, "The video was not found.") from None
    except VideoConflict as error:
        raise HTTPException(409, str(error)) from None
    except TemporaryStorageError:
        raise HTTPException(503, "Object storage is temporarily unavailable.") from None
    return VideoRetry(
        video_id=str(result.video_id),
        status="QUEUED",
        processing_job_id=str(result.job_id),
        attempt=result.number,
    )
