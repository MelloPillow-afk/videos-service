"""Custom thumbnails: direct uploads, starting their rendering, and removing them."""

from dataclasses import replace
from uuid import UUID, uuid4

from src.clients import cloudflare
from src.clients.cloudflare import PresignedUpload
from src.config import Settings
from src.domain.jobs import Job, JobKind
from src.domain.videos import (
    UploadMissing,
    UploadNotCurrent,
    UploadSizeMismatch,
    UploadTooLarge,
    Video,
    VideoNotFound,
)
from src.repositories import jobs as jobs_repository
from src.repositories import videos as videos_repository
from src.services import jobs as jobs_service
from src.services import videos as videos_service


async def create_upload(
    video_id: UUID, content_type: str, size_bytes: int, settings: Settings
) -> tuple[Video, PresignedUpload]:
    """Give the video a new current thumbnail upload and a URL to upload the image to."""
    if size_bytes > settings.max_thumbnail_bytes:
        raise UploadTooLarge(video_id)
    video = await videos_service.get_video(video_id)
    upload_id = uuid4()
    key = f"videos/{video.id}/thumbnails/{upload_id}/source"
    started = await videos_repository.start_thumbnail_upload(
        replace(
            video,
            thumbnail_upload_id=upload_id,
            thumbnail_upload_key=key,
            thumbnail_upload_size_bytes=size_bytes,
        )
    )
    if started is None:
        raise VideoNotFound(video_id)
    return started, cloudflare.presign_upload(key, content_type)


async def complete_upload(video_id: UUID, upload_id: UUID, settings: Settings) -> Job:
    """Accept the current thumbnail upload and start rendering it; return its job.

    Completing an upload that was already accepted returns its job without new work.
    """
    video = await videos_service.get_video(video_id)
    if video.thumbnail_upload_id != upload_id:
        raise UploadNotCurrent(upload_id)
    # The current upload has a job only once it is accepted.
    accepted = await jobs_repository.find_job(video.id, JobKind.CUSTOM_THUMBNAIL_PROCESSING)
    if accepted is not None:
        return accepted

    assert video.thumbnail_upload_key is not None
    size_bytes = await cloudflare.uploaded_size(video.thumbnail_upload_key)
    if size_bytes is None:
        raise UploadMissing(upload_id)
    if size_bytes > settings.max_thumbnail_bytes:
        raise UploadTooLarge(video_id)
    if size_bytes != video.thumbnail_upload_size_bytes:
        raise UploadSizeMismatch(upload_id)

    job_id = await videos_repository.accept_thumbnail_upload(video)
    if job_id is None:
        return await complete_upload(video_id, upload_id, settings)
    await jobs_service.launch(job_id, settings)
    return await jobs_service.get_job(job_id)


async def remove_custom_thumbnail(video_id: UUID) -> Video:
    """Show the generated thumbnail again, dropping the custom one and any pending upload."""
    video = await videos_service.get_video(video_id)
    removed = await videos_repository.remove_custom_thumbnail(
        replace(
            video,
            custom_thumbnail_prefix=None,
            thumbnail_upload_id=None,
            thumbnail_upload_key=None,
            thumbnail_upload_size_bytes=None,
        )
    )
    if removed is None:
        raise VideoNotFound(video_id)
    return removed
