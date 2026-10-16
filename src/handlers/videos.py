"""HTTP adapters for persisted video operations."""

from uuid import UUID

from fastapi import HTTPException, Request, Response

from src.domain.uploads import UploadRejected
from src.domain.videos import VideoConflict, VideoNotFound, VideoRecord
from src.handlers.dependencies import optional_admin, require_admin
from src.providers.storage import TemporaryStorageError
from src.schemas.generated.operations import (
    VideosCompleteUploadIdParameter,
    VideosGetVideoIdParameter,
    VideosUpdateVideoIdParameter,
    VideosUploadUrlIdParameter,
)
from src.schemas.generated.uploads import (
    SourceUpload,
    SourceUploadCreate,
    SourceUploadProcessing,
    UploadComplete,
)
from src.schemas.generated.videos import Video, VideoCreate, VideoUpdate
from src.services.uploads import SourceUploads
from src.services.videos import VideoService


def video_response(video: VideoRecord) -> Video:
    return Video.model_validate(
        {
            "id": str(video.id),
            "title": video.title,
            "description": video.description,
            "status": video.status,
            "publication_status": video.publication_status,
            "size_bytes": video.size_bytes,
            "duration_seconds": video.duration_seconds,
            "thumbnail": {
                "status": video.generated_thumbnail_status,
                "source": "NONE",
                "url": None,
            },
            "published_at": video.published_at.isoformat().replace("+00:00", "Z")
            if video.published_at
            else None,
            "created_at": video.created_at.isoformat().replace("+00:00", "Z"),
            "updated_at": video.updated_at.isoformat().replace("+00:00", "Z"),
        }
    )


async def create_video(*, body: VideoCreate, response: Response, request: Request) -> Video:
    await require_admin(request)
    service: VideoService = request.app.state.videos
    video = await service.create(body.title, body.description)
    response.headers["Location"] = f"/v1/videos/{video.id}"
    return video_response(video)


async def get_video(*, id: VideosGetVideoIdParameter, request: Request) -> Video:
    service: VideoService = request.app.state.videos
    try:
        return video_response(
            await service.get(UUID(id), administrator=await optional_admin(request))
        )
    except VideoNotFound:
        raise HTTPException(404, "The video was not found.") from None


async def update_video(
    *, id: VideosUpdateVideoIdParameter, body: VideoUpdate, request: Request
) -> Video:
    await require_admin(request)
    service: VideoService = request.app.state.videos
    try:
        return video_response(await service.update(UUID(id), body.model_dump(exclude_unset=True)))
    except VideoNotFound:
        raise HTTPException(404, "The video was not found.") from None
    except VideoConflict as error:
        raise HTTPException(409, str(error)) from None


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
        raise HTTPException(error.status, error.message) from None
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
        raise HTTPException(error.status, error.message) from None
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
