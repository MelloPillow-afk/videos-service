"""HTTP handlers for a video's custom thumbnail."""

from typing import Annotated
from uuid import UUID

from fastapi import HTTPException, Path, Request, Response

from src.domain import videos as domain
from src.handlers.jobs import job_resource
from src.handlers.utilities import thumbnail, timestamp
from src.schemas.generated.jobs import Job
from src.schemas.generated.operations import (
    AdminThumbnailsCompleteUploadIdParameter,
    AdminThumbnailsDeleteThumbnailIdParameter,
    AdminThumbnailsUploadUrlIdParameter,
)
from src.schemas.generated.thumbnails import Thumbnail, ThumbnailUpload, ThumbnailUploadCreate
from src.schemas.generated.uploads import Upload, UploadComplete, UploadHeaders
from src.services import thumbnails as thumbnails_service

_NOT_FOUND = "The video was not found."
_TOO_LARGE = "The file exceeds the configured size limit."


async def upload_url(
    *,
    id: Annotated[AdminThumbnailsUploadUrlIdParameter, Path(alias="id", description="Video ID.")],
    body: ThumbnailUploadCreate,
    request: Request,
) -> ThumbnailUpload:
    try:
        video, upload = await thumbnails_service.create_upload(
            UUID(id), body.content_type, body.size_bytes, request.app.state.settings
        )
    except domain.VideoNotFound:
        raise HTTPException(status_code=404, detail=_NOT_FOUND) from None
    except domain.UploadTooLarge:
        raise HTTPException(status_code=413, detail=_TOO_LARGE) from None
    assert video.thumbnail_upload_id is not None  # Starting an upload sets it.
    return ThumbnailUpload(
        video_id=str(video.id),
        upload=Upload(
            upload_id=str(video.thumbnail_upload_id),
            method="PUT",
            url=upload.url,
            headers=UploadHeaders.model_validate({"Content-Type": body.content_type}),
            expires_at=timestamp(upload.expires_at),
        ),
    )


async def complete_upload(
    *,
    id: Annotated[
        AdminThumbnailsCompleteUploadIdParameter, Path(alias="id", description="Video ID.")
    ],
    body: UploadComplete,
    response: Response,
    request: Request,
) -> Job:
    try:
        job = await thumbnails_service.complete_upload(
            UUID(id), UUID(body.upload_id), request.app.state.settings
        )
    except domain.VideoNotFound:
        raise HTTPException(status_code=404, detail=_NOT_FOUND) from None
    except domain.UploadMissing:
        raise HTTPException(status_code=404, detail="The uploaded file was not found.") from None
    except domain.UploadTooLarge:
        raise HTTPException(status_code=413, detail=_TOO_LARGE) from None
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


async def delete_thumbnail(
    *,
    id: Annotated[
        AdminThumbnailsDeleteThumbnailIdParameter, Path(alias="id", description="Video ID.")
    ],
) -> Thumbnail:
    try:
        video = await thumbnails_service.remove_custom_thumbnail(UUID(id))
    except domain.VideoNotFound:
        raise HTTPException(status_code=404, detail=_NOT_FOUND) from None
    return Thumbnail(video_id=str(video.id), thumbnail=thumbnail(video))
