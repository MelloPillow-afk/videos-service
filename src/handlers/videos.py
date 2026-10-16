"""HTTP adapters for persisted video operations."""

from uuid import UUID

from fastapi import HTTPException, Request, Response

from src.domain.library import InvalidCursor, LibraryQuery
from src.domain.videos import VideoConflict, VideoNotFound
from src.handlers.dependencies import optional_admin, require_admin
from src.handlers.video_projection import video_response
from src.schemas.generated.operations import (
    VideosGetVideoIdParameter,
    VideosListVideosCursorParameter,
    VideosListVideosLimitParameter,
    VideosListVideosSearchParameter,
    VideosUpdateVideoIdParameter,
)
from src.schemas.generated.videos import (
    PublicationStatus,
    Video,
    VideoCreate,
    Videos,
    VideoStatus,
    VideoUpdate,
)
from src.services.library import LibraryService
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
