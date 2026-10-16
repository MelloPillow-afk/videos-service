"""Custom-thumbnail HTTP adapters."""

from uuid import UUID

from fastapi import HTTPException, Request

from src.domain.uploads import UploadRejected
from src.domain.videos import VideoConflict, VideoNotFound, VideoRecord
from src.handlers.dependencies import require_admin
from src.handlers.video_projection import video_response
from src.providers.storage import StorageLimitError, StorageMissingError, TemporaryStorageError
from src.schemas.generated.operations import (
    ThumbnailsCompleteUploadIdParameter,
    ThumbnailsDeleteThumbnailIdParameter,
    ThumbnailsUploadUrlIdParameter,
)
from src.schemas.generated.thumbnails import Thumbnail, ThumbnailUpload, ThumbnailUploadCreate
from src.schemas.generated.uploads import UploadComplete
from src.services.thumbnails import CustomThumbnails


def thumbnail_response(video: VideoRecord, request: Request) -> Thumbnail:
    return Thumbnail(
        video_id=str(video.id),
        thumbnail=video_response(video, request.app.state.settings.cdn_origin).thumbnail,
    )


def http_error(error: Exception) -> HTTPException:
    if isinstance(error, UploadRejected):
        return HTTPException(error.status, error.message)
    if isinstance(error, VideoNotFound):
        return HTTPException(404, "The video was not found.")
    if isinstance(error, VideoConflict):
        return HTTPException(409, str(error))
    if isinstance(error, StorageLimitError):
        return HTTPException(413, "The image exceeds the configured size limit.")
    if isinstance(error, StorageMissingError):
        return HTTPException(404, "The uploaded image was not found.")
    return HTTPException(503, "Object storage is temporarily unavailable.")


async def upload_url(
    *, id: ThumbnailsUploadUrlIdParameter, body: ThumbnailUploadCreate, request: Request
) -> ThumbnailUpload:
    await require_admin(request)
    service: CustomThumbnails = request.app.state.thumbnails
    try:
        attempt, upload = await service.issue(UUID(id), body.content_type, body.size_bytes)
    except (UploadRejected, VideoConflict, VideoNotFound, TemporaryStorageError) as error:
        raise http_error(error) from None
    return ThumbnailUpload.model_validate(
        {
            "video_id": id,
            "upload": {
                "upload_id": str(attempt.id),
                "method": upload.method,
                "url": upload.url,
                "headers": upload.headers,
                "expires_at": attempt.expires_at.isoformat().replace("+00:00", "Z"),
            },
        }
    )


async def complete_upload(
    *, id: ThumbnailsCompleteUploadIdParameter, body: UploadComplete, request: Request
) -> Thumbnail:
    await require_admin(request)
    service: CustomThumbnails = request.app.state.thumbnails
    try:
        return thumbnail_response(await service.confirm(UUID(id), UUID(body.upload_id)), request)
    except (
        UploadRejected,
        VideoConflict,
        VideoNotFound,
        TemporaryStorageError,
        StorageMissingError,
        StorageLimitError,
    ) as error:
        raise http_error(error) from None


async def delete_thumbnail(
    *, id: ThumbnailsDeleteThumbnailIdParameter, request: Request
) -> Thumbnail:
    await require_admin(request)
    service: CustomThumbnails = request.app.state.thumbnails
    try:
        return thumbnail_response(await service.remove(UUID(id)), request)
    except (VideoConflict, VideoNotFound) as error:
        raise http_error(error) from None
