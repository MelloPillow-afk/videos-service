"""A video's media: turning its accepted upload into HLS playback and a generated thumbnail."""

import logging
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import UUID

from src.clients import cloudflare, ffmpeg
from src.clients.ffmpeg import MediaInfo, Rendition
from src.config import Settings
from src.domain.jobs import Job, JobKind
from src.domain.videos import InvalidMedia, Video, VideoChanged, VideoNotFound, VideoStatus
from src.repositories import jobs as jobs_repository
from src.repositories import videos as videos_repository
from src.services import videos as videos_service

logger = logging.getLogger(__name__)

# Shorter-side sizes and video bitrates; renditions never upscale the source.
_LADDER = ((360, 800), (720, 2800), (1080, 5000))
_THUMBNAIL_SIZE = (1280, 720)


async def run_job(job_id: UUID, settings: Settings) -> None:
    """Run a queued job once, recording its success or failure."""
    job = await jobs_repository.start_job(job_id)
    if job is None:
        logger.warning("Job %s is not queued; nothing to run", job_id)
        return
    try:
        video = await videos_service.get_video(job.video_id)
        with TemporaryDirectory() as work:
            if job.kind is JobKind.VIDEO_PROCESSING:
                await _process_video(job, video, Path(work), settings)
            elif job.kind is JobKind.THUMBNAIL_GENERATION:
                await _generate_thumbnail(job, video, Path(work), settings)
            else:
                raise ValueError(f"Workers do not run {job.kind} jobs")
    except InvalidMedia as error:
        await jobs_repository.fail_job(job.id, str(error))
    except (VideoNotFound, VideoChanged):
        await jobs_repository.fail_job(job.id, "The video changed while it was processed.")
    except Exception:
        logger.exception("Job %s failed", job.id)
        await jobs_repository.fail_job(job.id, "Processing failed.")


async def _process_video(job: Job, video: Video, work: Path, settings: Settings) -> None:
    source = await _download(video, work)
    media = await _inspect(source, settings)
    hls = work / "hls"
    await ffmpeg.make_hls(source, hls, renditions(media), has_audio=media.has_audio)
    prefix = f"{_output_prefix(video)}/hls"
    master = hls / "master.m3u8"
    # The master playlist goes last, so it never lists missing renditions.
    for path in sorted(path for path in hls.rglob("*") if path.is_file() and path != master):
        await cloudflare.upload_media(path, f"{prefix}/{path.relative_to(hls).as_posix()}")
    await cloudflare.upload_media(master, f"{prefix}/master.m3u8")
    processed = replace(
        video,
        status=VideoStatus.READY,
        playback_key=f"{prefix}/master.m3u8",
        duration_seconds=media.duration_seconds,
    )
    if not await videos_repository.finish_processing(processed, job.id):
        raise VideoChanged(video.id)


async def _generate_thumbnail(job: Job, video: Video, work: Path, settings: Settings) -> None:
    source = await _download(video, work)
    media = await _inspect(source, settings)
    thumbnail = work / "thumbnail.jpg"
    width, height = _THUMBNAIL_SIZE
    await ffmpeg.make_thumbnail(
        source,
        thumbnail,
        # Early, but past any opening black frame when the video is long enough.
        at_seconds=min(1.0, media.duration_seconds / 2),
        width=width,
        height=height,
    )
    key = f"{_output_prefix(video)}/thumbnail.jpg"
    await cloudflare.upload_media(thumbnail, key)
    if not await videos_repository.finish_thumbnail(
        replace(video, generated_thumbnail_key=key), job.id
    ):
        raise VideoChanged(video.id)


async def _download(video: Video, work: Path) -> Path:
    assert video.source_key is not None  # Only accepted uploads have jobs.
    source = work / "source.mp4"
    await cloudflare.download_source(video.source_key, source)
    return source


async def _inspect(source: Path, settings: Settings) -> MediaInfo:
    media = await ffmpeg.probe(source)
    if media is None or "mp4" not in media.format_names:
        raise InvalidMedia("The file is not a playable MP4 video.")
    if media.duration_seconds > settings.max_duration_seconds:
        raise InvalidMedia(f"The video is longer than {settings.max_duration_seconds:g} seconds.")
    return media


def renditions(media: MediaInfo) -> list[Rendition]:
    """Each ladder size the source reaches, or one rendition at the source size."""
    short_side = min(media.width, media.height)
    ladder = [(size, kbps) for size, kbps in _LADDER if size <= short_side]
    if not ladder:
        ladder = [(short_side - short_side % 2, _LADDER[0][1])]
    return [_rendition(media, size, kbps) for size, kbps in ladder]


def _rendition(media: MediaInfo, short_side: int, kbps: int) -> Rendition:
    long_side = round(short_side * max(media.width, media.height) / min(media.width, media.height))
    long_side += long_side % 2  # H.264 needs even dimensions.
    landscape = media.width >= media.height
    return Rendition(
        name=f"{short_side}p",
        width=long_side if landscape else short_side,
        height=short_side if landscape else long_side,
        video_kbps=kbps,
    )


def _output_prefix(video: Video) -> str:
    return f"videos/{video.id}/uploads/{video.upload_id}"
