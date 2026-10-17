"""The worker turns an accepted upload into HLS playback and a thumbnail with real FFmpeg."""

import subprocess
from pathlib import Path
from typing import Any, LiteralString, cast
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from psycopg import AsyncConnection

from src.clients import cloudflare, ffmpeg
from src.config import Settings
from src.libs.thumbnails import SIZES
from src.workers.media import run
from tests.fakes import FakeStorage
from tests.rows import insert_video

pytestmark = pytest.mark.integration

FIXTURES = Path(__file__).parent.parent / "fixtures"


def make_video(path: Path, size: str, seconds: int) -> bytes:
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y",
         "-f", "lavfi", "-i", f"testsrc2=size={size}:rate=24:duration={seconds}",
         "-f", "lavfi", "-i", f"sine=frequency=440:duration={seconds}",
         "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(path)],
        check=True,
    )  # fmt: skip
    return path.read_bytes()


@pytest.fixture(scope="session")
def landscape_mp4(tmp_path_factory: pytest.TempPathFactory) -> bytes:
    return make_video(tmp_path_factory.mktemp("media") / "landscape.mp4", "1280x720", 2)


@pytest.fixture
def settings(api_app: FastAPI) -> Settings:
    return api_app.state.settings


async def accepted_video(
    db: AsyncConnection, storage: FakeStorage, source: bytes
) -> tuple[str, UUID, dict[str, UUID]]:
    """A processing video whose upload was accepted, with its two queued jobs."""
    upload_id = uuid4()
    video_id = str(uuid4())
    source_key = f"videos/{video_id}/uploads/{upload_id}/source.mp4"
    await insert_video(
        db,
        id=video_id,
        status="PROCESSING",
        upload_id=upload_id,
        source_key=source_key,
        size_bytes=len(source),
    )
    storage.files[source_key] = source
    cursor = await db.execute(
        "INSERT INTO jobs (video_id, kind) VALUES "
        "(%(id)s, 'VIDEO_PROCESSING'), (%(id)s, 'THUMBNAIL_GENERATION') RETURNING kind, id",
        {"id": video_id},
    )
    return video_id, upload_id, {kind: id_ for kind, id_ in await cursor.fetchall()}


async def job_row(db: AsyncConnection, job_id: UUID) -> tuple[Any, ...] | None:
    cursor = await db.execute("SELECT status, message FROM jobs WHERE id = %s", (job_id,))
    return await cursor.fetchone()


async def video_media(db: AsyncConnection, video_id: str) -> tuple[Any, ...] | None:
    cursor = await db.execute(
        "SELECT status, playback_key, duration_seconds::float, generated_thumbnail_prefix "
        "FROM videos WHERE id = %s",
        (video_id,),
    )
    return await cursor.fetchone()


async def test_video_job_publishes_hls_and_readies_the_video(
    db: AsyncConnection, storage: FakeStorage, settings: Settings, landscape_mp4: bytes
) -> None:
    video_id, upload_id, jobs = await accepted_video(db, storage, landscape_mp4)

    await run(jobs["VIDEO_PROCESSING"], settings)

    prefix = f"videos/{video_id}/uploads/{upload_id}/hls"
    assert await job_row(db, jobs["VIDEO_PROCESSING"]) == ("SUCCEEDED", None)
    assert await video_media(db, video_id) == ("READY", f"{prefix}/master.m3u8", 2.0, None)
    master = storage.media[f"{prefix}/master.m3u8"].decode()
    # A 720p source gets 360p and 720p renditions, and no upscaled 1080p.
    assert "RESOLUTION=640x360" in master and "RESOLUTION=1280x720" in master
    assert "1080" not in master
    for rendition in ("360p", "720p"):
        assert f"{rendition}/index.m3u8" in master
        assert f"{prefix}/{rendition}/segment_000.ts" in storage.media
    assert await job_row(db, jobs["THUMBNAIL_GENERATION"]) == ("QUEUED", None)


async def published_size(storage: FakeStorage, key: str, tmp_path: Path) -> tuple[int, int]:
    image = tmp_path / "published.jpg"
    image.write_bytes(storage.media[key])
    info = await ffmpeg.probe_image(image)
    assert info is not None and info.codec == "mjpeg"
    return info.width, info.height


async def test_thumbnail_job_publishes_a_frame_at_every_size(
    db: AsyncConnection,
    storage: FakeStorage,
    settings: Settings,
    tmp_path: Path,
    landscape_mp4: bytes,
) -> None:
    video_id, upload_id, jobs = await accepted_video(db, storage, landscape_mp4)

    await run(jobs["THUMBNAIL_GENERATION"], settings)

    prefix = f"videos/{video_id}/uploads/{upload_id}/thumbnails"
    assert await job_row(db, jobs["THUMBNAIL_GENERATION"]) == ("SUCCEEDED", None)
    assert await video_media(db, video_id) == ("PROCESSING", None, None, prefix)
    for name, size in SIZES.items():
        assert await published_size(storage, f"{prefix}/{name}.jpg", tmp_path) == size


async def test_portrait_video_is_thumbnailed_inside_a_padded_frame(
    db: AsyncConnection, storage: FakeStorage, settings: Settings, tmp_path: Path
) -> None:
    portrait = make_video(tmp_path / "portrait.mp4", "360x640", 1)
    video_id, upload_id, jobs = await accepted_video(db, storage, portrait)

    await run(jobs["VIDEO_PROCESSING"], settings)
    await run(jobs["THUMBNAIL_GENERATION"], settings)

    master = storage.media[f"videos/{video_id}/uploads/{upload_id}/hls/master.m3u8"]
    assert b"RESOLUTION=360x640" in master
    key = f"videos/{video_id}/uploads/{upload_id}/thumbnails/xl.jpg"
    assert await published_size(storage, key, tmp_path) == (1280, 720)


async def test_file_that_is_not_a_video_fails_the_video(
    db: AsyncConnection, storage: FakeStorage, settings: Settings
) -> None:
    video_id, _, jobs = await accepted_video(db, storage, b"not a video")

    await run(jobs["VIDEO_PROCESSING"], settings)

    assert await job_row(db, jobs["VIDEO_PROCESSING"]) == (
        "FAILED",
        "The file is not a playable MP4 video.",
    )
    media = await video_media(db, video_id)
    assert media is not None and media[0] == "FAILED"
    assert storage.media == {}


async def test_video_over_the_duration_limit_fails(
    db: AsyncConnection, storage: FakeStorage, settings: Settings, landscape_mp4: bytes
) -> None:
    video_id, _, jobs = await accepted_video(db, storage, landscape_mp4)

    await run(jobs["VIDEO_PROCESSING"], settings.model_copy(update={"max_duration_seconds": 1}))

    assert await job_row(db, jobs["VIDEO_PROCESSING"]) == (
        "FAILED",
        "The video is longer than 1 seconds.",
    )
    media = await video_media(db, video_id)
    assert media is not None and media[0] == "FAILED"


async def test_failed_thumbnail_leaves_the_video_processing(
    db: AsyncConnection, storage: FakeStorage, settings: Settings
) -> None:
    video_id, _, jobs = await accepted_video(db, storage, b"not a video")

    await run(jobs["THUMBNAIL_GENERATION"], settings)

    row = await job_row(db, jobs["THUMBNAIL_GENERATION"])
    assert row is not None and row[0] == "FAILED"
    media = await video_media(db, video_id)
    assert media is not None and media[0] == "PROCESSING"


async def test_job_that_is_not_queued_does_not_run(
    db: AsyncConnection, storage: FakeStorage, settings: Settings, landscape_mp4: bytes
) -> None:
    video_id, _, jobs = await accepted_video(db, storage, landscape_mp4)
    await db.execute(
        "UPDATE jobs SET status = 'RUNNING' WHERE id = %s", (jobs["VIDEO_PROCESSING"],)
    )

    await run(jobs["VIDEO_PROCESSING"], settings)

    assert await job_row(db, jobs["VIDEO_PROCESSING"]) == ("RUNNING", None)
    assert await video_media(db, video_id) == ("PROCESSING", None, None, None)


async def test_deleted_video_is_not_processed(
    db: AsyncConnection, storage: FakeStorage, settings: Settings, landscape_mp4: bytes
) -> None:
    video_id, _, jobs = await accepted_video(db, storage, landscape_mp4)
    await db.execute("UPDATE videos SET deleted_at = now() WHERE id = %s", (video_id,))

    await run(jobs["THUMBNAIL_GENERATION"], settings)

    assert await job_row(db, jobs["THUMBNAIL_GENERATION"]) == (
        "FAILED",
        "The video changed while it was processed.",
    )
    assert storage.media == {}


async def test_results_are_not_saved_when_the_job_finished_meanwhile(
    db: AsyncConnection,
    storage: FakeStorage,
    settings: Settings,
    landscape_mp4: bytes,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    video_id, _, jobs = await accepted_video(db, storage, landscape_mp4)
    job_id = jobs["THUMBNAIL_GENERATION"]

    async def upload_then_fail_the_job(path: Path, key: str) -> None:
        await storage.upload_media(path, key)
        await db.execute(
            "UPDATE jobs SET status = 'FAILED', message = 'x' WHERE id = %s", (job_id,)
        )

    monkeypatch.setattr(cloudflare, "upload_media", upload_then_fail_the_job)

    await run(job_id, settings)

    assert await job_row(db, job_id) == ("FAILED", "x")
    assert await video_media(db, video_id) == ("PROCESSING", None, None, None)


async def test_unexpected_errors_fail_the_job(
    db: AsyncConnection,
    storage: FakeStorage,
    settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, _, jobs = await accepted_video(db, storage, b"unread")

    async def unavailable(_key: str, _path: Path) -> None:
        raise ConnectionError("R2 is unavailable")

    monkeypatch.setattr(cloudflare, "download_source", unavailable)

    await run(jobs["VIDEO_PROCESSING"], settings)

    assert await job_row(db, jobs["VIDEO_PROCESSING"]) == ("FAILED", "Processing failed.")


def make_image(path: Path, size: str) -> bytes:
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"testsrc2=size={size}",
         "-frames:v", "1", str(path)],
        check=True,
    )  # fmt: skip
    return path.read_bytes()


async def accepted_thumbnail(
    db: AsyncConnection, storage: FakeStorage, image: bytes
) -> tuple[str, str, UUID]:
    """A video whose custom thumbnail upload was accepted, with its queued job; returns
    the video ID, where the rendered sizes go, and the job ID."""
    video_id = str(uuid4())
    upload_id = uuid4()
    key = f"videos/{video_id}/thumbnails/{upload_id}/source"
    await insert_video(
        db,
        id=video_id,
        thumbnail_upload_id=upload_id,
        thumbnail_upload_key=key,
        thumbnail_upload_size_bytes=len(image),
    )
    storage.files[key] = image
    cursor = await db.execute(
        "INSERT INTO jobs (video_id, kind) VALUES (%s, 'CUSTOM_THUMBNAIL_PROCESSING') RETURNING id",
        (video_id,),
    )
    row = await cursor.fetchone()
    assert row is not None
    return video_id, f"videos/{video_id}/thumbnails/{upload_id}", row[0]


async def custom_prefix(db: AsyncConnection, video_id: str) -> str | None:
    cursor = await db.execute(
        "SELECT custom_thumbnail_prefix FROM videos WHERE id = %s", (video_id,)
    )
    row = await cursor.fetchone()
    assert row is not None
    return row[0]


@pytest.mark.parametrize(
    ("file_name", "size"),
    # FFmpeg builds may lack a WebP encoder, so the WebP image is a fixture.
    [("cover.png", "1920x1080"), ("cover.jpg", "1366x768"), ("cover-1280x720.webp", None)],
)
async def test_custom_thumbnail_is_rendered_at_every_size(
    db: AsyncConnection,
    storage: FakeStorage,
    settings: Settings,
    tmp_path: Path,
    file_name: str,
    size: str | None,
) -> None:
    image = (
        (FIXTURES / file_name).read_bytes()
        if size is None
        else make_image(tmp_path / file_name, size)
    )
    video_id, prefix, job_id = await accepted_thumbnail(db, storage, image)

    await run(job_id, settings)

    assert await job_row(db, job_id) == ("SUCCEEDED", None)
    assert await custom_prefix(db, video_id) == prefix
    for name, dimensions in SIZES.items():
        assert await published_size(storage, f"{prefix}/{name}.jpg", tmp_path) == dimensions


@pytest.mark.parametrize(
    ("file_name", "size", "message"),
    [
        ("cover.png", "1600x1200", "The image is not landscape 16:9."),
        ("cover.png", "1080x1920", "The image is not landscape 16:9."),
        ("cover.png", "640x360", "The image is smaller than 1280 × 720."),
        ("cover.mp4", "1280x720", "The file is not a JPEG, PNG, or WebP image."),
    ],
)
async def test_unsuitable_custom_thumbnail_fails_its_job(
    db: AsyncConnection,
    storage: FakeStorage,
    settings: Settings,
    tmp_path: Path,
    file_name: str,
    size: str,
    message: str,
) -> None:
    image = make_image(tmp_path / file_name, size)
    video_id, _, job_id = await accepted_thumbnail(db, storage, image)

    await run(job_id, settings)

    assert await job_row(db, job_id) == ("FAILED", message)
    assert await custom_prefix(db, video_id) is None
    assert storage.media == {}


@pytest.mark.parametrize("audio", [False, True])
async def test_file_that_is_not_an_image_fails_its_job(
    db: AsyncConnection, storage: FakeStorage, settings: Settings, tmp_path: Path, audio: bool
) -> None:
    file = b"not an image"
    if audio:  # Readable media, but without a picture.
        sound = tmp_path / "cover.wav"
        subprocess.run(
            ["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "sine=duration=1", str(sound)],
            check=True,
        )
        file = sound.read_bytes()
    video_id, _, job_id = await accepted_thumbnail(db, storage, file)

    await run(job_id, settings)

    assert await job_row(db, job_id) == ("FAILED", "The file is not a JPEG, PNG, or WebP image.")
    assert await custom_prefix(db, video_id) is None


@pytest.mark.parametrize(
    "change",
    [
        "UPDATE videos SET thumbnail_upload_id = gen_random_uuid() WHERE id = %s",
        "UPDATE videos SET thumbnail_upload_id = NULL, thumbnail_upload_key = NULL WHERE id = %s",
    ],
)
async def test_replaced_or_removed_custom_thumbnail_is_not_shown(
    db: AsyncConnection,
    storage: FakeStorage,
    settings: Settings,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    change: str,
) -> None:
    image = make_image(tmp_path / "cover.png", "1280x720")
    video_id, _, job_id = await accepted_thumbnail(db, storage, image)

    async def upload_then_change_the_upload(path: Path, key: str) -> None:
        await storage.upload_media(path, key)
        await db.execute(cast(LiteralString, change), (video_id,))

    monkeypatch.setattr(cloudflare, "upload_media", upload_then_change_the_upload)

    await run(job_id, settings)

    assert await job_row(db, job_id) == ("FAILED", "The video changed while it was processed.")
    assert await custom_prefix(db, video_id) is None


async def test_custom_thumbnail_removed_before_its_job_runs_is_not_rendered(
    db: AsyncConnection, storage: FakeStorage, settings: Settings, tmp_path: Path
) -> None:
    image = make_image(tmp_path / "cover.png", "1280x720")
    video_id, _, job_id = await accepted_thumbnail(db, storage, image)
    await db.execute(
        "UPDATE videos SET thumbnail_upload_id = NULL, thumbnail_upload_key = NULL WHERE id = %s",
        (video_id,),
    )

    await run(job_id, settings)

    assert await job_row(db, job_id) == ("FAILED", "The video changed while it was processed.")
    assert storage.media == {}
