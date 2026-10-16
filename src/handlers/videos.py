"""HTTP adapters for persisted video operations."""

from uuid import UUID

from fastapi import HTTPException, Request, Response

from src.domain.videos import VideoConflict, VideoNotFound, VideoRecord
from src.handlers.dependencies import optional_admin, require_admin
from src.schemas.generated.operations import VideosGetVideoIdParameter, VideosUpdateVideoIdParameter
from src.schemas.generated.videos import Video, VideoCreate, VideoUpdate
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
        | (
            {
                "processing_error": {
                    "code": video.processing_error_code,
                    "message": video.processing_error_message,
                }
            }
            if video.processing_error_code
            else {}
        )
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
