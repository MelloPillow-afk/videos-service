"""Direct uploads of a video's source file, and starting its processing."""

from dataclasses import replace
from uuid import UUID, uuid4

from src.clients import cloudflare
from src.clients.cloudflare import PresignedUpload
from src.config import Settings
from src.domain.jobs import Job, JobKind
from src.domain.videos import (
    UploadMissing,
    UploadNotAllowed,
    UploadNotCurrent,
    UploadSizeMismatch,
    UploadTooLarge,
    Video,
    VideoStatus,
)
from src.repositories import videos as videos_repository
from src.services import jobs as jobs_service
from src.services import videos as videos_service


async def create_upload(
    video_id: UUID, content_type: str, size_bytes: int, settings: Settings
) -> tuple[Video, PresignedUpload]:
    """Give the video a new current upload and a URL to upload its file to."""
    if size_bytes > settings.max_upload_bytes:
        raise UploadTooLarge(video_id)
    video = await videos_service.get_video(video_id)
    if video.status not in (VideoStatus.CREATED, VideoStatus.UPLOADING):
        raise UploadNotAllowed(video_id)
    upload_id = uuid4()
    source_key = f"videos/{video.id}/uploads/{upload_id}/source.mp4"
    started = await videos_repository.start_upload(
        replace(
            video,
            status=VideoStatus.UPLOADING,
            upload_id=upload_id,
            source_key=source_key,
            size_bytes=size_bytes,
        )
    )
    if started is None:
        raise UploadNotAllowed(video_id)
    return started, cloudflare.presign_upload(source_key, content_type)


async def complete_upload(video_id: UUID, upload_id: UUID, settings: Settings) -> Job:
    """Accept the current upload's file and start processing it; return the video job.

    Completing an upload that was already accepted returns its job without new work.
    """
    video = await videos_service.get_video(video_id)
    if video.upload_id == upload_id and video.status not in (
        VideoStatus.CREATED,
        VideoStatus.UPLOADING,
    ):
        assert video.latest_job_id is not None
        return await jobs_service.get_job(video.latest_job_id)
    if video.status is not VideoStatus.UPLOADING:
        raise UploadNotAllowed(video_id)
    if video.upload_id != upload_id:
        raise UploadNotCurrent(upload_id)

    assert video.source_key is not None
    size_bytes = await cloudflare.uploaded_size(video.source_key)
    if size_bytes is None:
        raise UploadMissing(upload_id)
    if size_bytes > settings.max_upload_bytes:
        raise UploadTooLarge(video_id)
    if size_bytes != video.size_bytes:
        raise UploadSizeMismatch(upload_id)

    job_ids = await videos_repository.accept_upload(
        replace(video, status=VideoStatus.PROCESSING, size_bytes=size_bytes)
    )
    if job_ids is None:
        return await complete_upload(video_id, upload_id, settings)
    await jobs_service.launch(job_ids[JobKind.VIDEO_PROCESSING], settings)
    await jobs_service.launch(job_ids[JobKind.THUMBNAIL_GENERATION], settings)
    return await jobs_service.get_job(job_ids[JobKind.VIDEO_PROCESSING])
