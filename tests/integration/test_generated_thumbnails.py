"""Independent thumbnail outcomes through HTTP with PostgreSQL and real FFmpeg."""

import asyncio
import subprocess
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlsplit
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from psycopg import AsyncConnection, sql

from src.config import Settings
from src.providers.storage import StorageArea, TemporaryStorageError
from src.worker import run_job
from tests.providers import LocalSigningKeys
from tests.storage_provider import MemoryStorage

pytestmark = pytest.mark.integration


@pytest_asyncio.fixture
async def thumbnail_client(
    api_app: FastAPI, signing_keys: LocalSigningKeys
) -> AsyncIterator[AsyncClient]:
    async with (
        api_app.router.lifespan_context(api_app),
        AsyncClient(
            transport=ASGITransport(app=api_app),
            base_url="http://test",
            headers={"Authorization": "Bearer " + signing_keys.token()},
        ) as client,
    ):
        yield client


def source_video(path: Path, *, size: str = "180x320") -> bytes:
    subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"color=c=lime:s={size}:r=5:d=1",
            "-c:v",
            "libx264",
            "-threads",
            "2",
            "-preset",
            "ultrafast",
            "-pix_fmt",
            "yuv420p",
            str(path),
        ],
        check=True,
        capture_output=True,
    )
    return path.read_bytes()


async def seed_thumbnail(
    client: AsyncClient,
    test_database: tuple[str, str],
    storage: MemoryStorage,
    source: bytes,
    *,
    status: str = "PROCESSING",
) -> tuple[str, UUID]:
    draft = await client.post("/v1/videos", json={"title": "Independent thumbnail"})
    assert draft.status_code == 201
    video_id, job_id = draft.json()["id"], uuid4()
    source_key = f"videos/{video_id}/source.mp4"
    storage.objects[("private", source_key)] = source, "video/mp4"
    url, schema = test_database
    async with await AsyncConnection.connect(url, autocommit=True) as connection:
        await connection.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(schema)))
        await connection.execute(
            "UPDATE videos SET status=%s,source_key=%s,size_bytes=%s WHERE id=%s",
            (status, source_key, len(source), video_id),
        )
        await connection.execute(
            """INSERT INTO jobs(id,video_id,kind,output_prefix,created_at,updated_at)
            VALUES (%s,%s,'THUMBNAIL',%s,%s,%s)""",
            (
                job_id,
                video_id,
                f"videos/{video_id}/jobs/{job_id}/",
                datetime.now(UTC),
                datetime.now(UTC),
            ),
        )
    return draft.headers["Location"], job_id


@pytest.mark.parametrize("status", ["QUEUED", "PROCESSING", "FAILED", "READY"])
async def test_generated_thumbnail_finishes_without_changing_video_processing(
    thumbnail_client: AsyncClient,
    api_app: FastAPI,
    storage: MemoryStorage,
    test_database: tuple[str, str],
    tmp_path: Path,
    status: str,
) -> None:
    path, job = await seed_thumbnail(
        thumbnail_client,
        test_database,
        storage,
        source_video(tmp_path / "portrait.mp4"),
        status=status,
    )
    await run_job(job, api_app.state.database, storage, Settings())
    video = (await thumbnail_client.get(path)).json()
    assert video["status"] == status
    assert video["publication_status"] == "DRAFT"
    assert video["thumbnail"]["status"] == "READY"
    assert video["thumbnail"]["source"] == "GENERATED"


def decoded_pixels(path: Path, image: bytes) -> bytes:
    path.write_bytes(image)
    dimensions = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height",
            "-of",
            "csv=p=0:s=x",
            str(path),
        ],
        check=True,
        capture_output=True,
    ).stdout.strip()
    assert dimensions == b"1280x720"
    return subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-i",
            str(path),
            "-frames:v",
            "1",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "rgb24",
            "pipe:1",
        ],
        check=True,
        capture_output=True,
    ).stdout


def pixel(data: bytes, x: int, y: int) -> tuple[int, int, int]:
    start = (y * 1280 + x) * 3
    return data[start], data[start + 1], data[start + 2]


@pytest.mark.parametrize(
    "shape", ["portrait", "landscape", "anamorphic", "rotated", "single-frame"]
)
async def test_fitted_canvas_preserves_display_aspect_and_black_padding(
    thumbnail_client: AsyncClient,
    api_app: FastAPI,
    storage: MemoryStorage,
    test_database: tuple[str, str],
    tmp_path: Path,
    shape: str,
) -> None:
    source_path = tmp_path / "source.mp4"
    source = source_video(
        source_path, size="320x180" if shape in ("landscape", "rotated") else "180x320"
    )
    if shape == "anamorphic":
        transformed = tmp_path / "anamorphic.mp4"
        subprocess.run(
            [
                "ffmpeg",
                "-v",
                "error",
                "-y",
                "-i",
                str(source_path),
                "-vf",
                "setsar=2",
                "-c:v",
                "libx264",
                "-threads",
                "2",
                str(transformed),
            ],
            check=True,
            capture_output=True,
        )
        source = transformed.read_bytes()
    if shape == "rotated":
        transformed = tmp_path / "rotated.mp4"
        subprocess.run(
            [
                "ffmpeg",
                "-v",
                "error",
                "-y",
                "-display_rotation:v:0",
                "90",
                "-i",
                str(source_path),
                "-c",
                "copy",
                "-metadata:s:v:0",
                "rotate=90",
                str(transformed),
            ],
            check=True,
            capture_output=True,
        )
        source = transformed.read_bytes()
    if shape == "single-frame":
        transformed = tmp_path / "single.mp4"
        subprocess.run(
            [
                "ffmpeg",
                "-v",
                "error",
                "-y",
                "-i",
                str(source_path),
                "-frames:v",
                "1",
                "-c:v",
                "libx264",
                "-threads",
                "2",
                str(transformed),
            ],
            check=True,
            capture_output=True,
        )
        source = transformed.read_bytes()
    location, job = await seed_thumbnail(thumbnail_client, test_database, storage, source)
    assert await run_job(job, api_app.state.database, storage, Settings())
    thumbnail = (await thumbnail_client.get(location)).json()["thumbnail"]
    key = urlsplit(str(thumbnail["url"])).path.lstrip("/")
    pixels = decoded_pixels(tmp_path / "image.jpg", await storage.read("public", key, 5242880))
    assert len(pixels) == 1280 * 720 * 3
    assert pixel(pixels, 640, 360)[1] > 220
    assert pixel(pixels, 640, 5)[1] > 220 and pixel(pixels, 640, 714)[1] > 220
    if shape == "landscape":
        assert pixel(pixels, 10, 360)[1] > 220
    else:
        assert max(pixel(pixels, 10, 360)) < 15 and max(pixel(pixels, 1269, 360)) < 15
        if shape == "anamorphic":
            assert pixel(pixels, 300, 360)[1] > 220
        else:
            assert max(pixel(pixels, 300, 360)) < 15


class ControlledThumbnailStorage(MemoryStorage):
    def __init__(self, *, fail_reads: int = 0, fail_writes: int = 0) -> None:
        super().__init__()
        self.fail_reads, self.fail_writes = fail_reads, fail_writes
        self.private_reads = 0
        self.pending_key: str | None = None
        self.write_started: asyncio.Event | None = None
        self.write_release: asyncio.Event | None = None

    async def read(self, area: StorageArea, key: str, max_bytes: int) -> bytes:
        if area == "private":
            self.private_reads += 1
            if self.fail_reads:
                self.fail_reads -= 1
                raise TemporaryStorageError
        return await super().read(area, key, max_bytes)

    async def write(
        self,
        area: StorageArea,
        key: str,
        data: bytes,
        content_type: str,
        *,
        create_only: bool = True,
    ) -> None:
        if area == "public":
            self.pending_key = key
        if area == "public" and self.write_started is not None and self.write_release is not None:
            self.write_started.set()
            await self.write_release.wait()
        await super().write(area, key, data, content_type, create_only=create_only)
        if area == "public" and self.fail_writes:
            self.fail_writes -= 1
            raise TemporaryStorageError


async def test_temporary_thumbnail_failures_have_three_independent_attempts(
    thumbnail_client: AsyncClient, api_app: FastAPI, test_database: tuple[str, str], tmp_path: Path
) -> None:
    storage = ControlledThumbnailStorage(fail_writes=2)
    path, job = await seed_thumbnail(
        thumbnail_client,
        test_database,
        storage,
        source_video(tmp_path / "source.mp4"),
        status="READY",
    )
    assert (
        await thumbnail_client.patch(path, json={"publication_status": "PUBLISHED"})
    ).status_code == 200
    delays: list[float] = []

    async def no_wait(delay: float) -> None:
        delays.append(delay)

    assert await run_job(job, api_app.state.database, storage, Settings(), sleep=no_wait)
    result = (await thumbnail_client.get(path)).json()
    assert result["status"] == "READY" and result["publication_status"] == "PUBLISHED"
    assert result["thumbnail"]["source"] == "GENERATED"
    assert storage.private_reads == 3 and delays == [1, 4]
    assert len(await storage.list("public", "videos/")) == 3
    url, schema = test_database
    async with await AsyncConnection.connect(url, autocommit=True) as connection:
        cursor = await connection.execute(
            sql.SQL(
                "SELECT execution_attempts,jsonb_array_length(output_keys) FROM {}.jobs WHERE id=%s"
            ).format(sql.Identifier(schema)),
            (job,),
        )
        assert await cursor.fetchone() == (3, 3)


@pytest.mark.parametrize("permanent", [False, True])
async def test_thumbnail_failure_does_not_change_video_readiness_or_publication(
    thumbnail_client: AsyncClient,
    api_app: FastAPI,
    test_database: tuple[str, str],
    tmp_path: Path,
    permanent: bool,
) -> None:
    storage = ControlledThumbnailStorage(fail_reads=0 if permanent else 10)
    source = b"corrupt MP4" if permanent else source_video(tmp_path / "source.mp4")
    path, job = await seed_thumbnail(
        thumbnail_client, test_database, storage, source, status="READY"
    )
    assert (
        await thumbnail_client.patch(path, json={"publication_status": "PUBLISHED"})
    ).status_code == 200
    delays: list[float] = []

    async def no_wait(delay: float) -> None:
        delays.append(delay)

    assert not await run_job(job, api_app.state.database, storage, Settings(), sleep=no_wait)
    result = (await thumbnail_client.get(path)).json()
    assert result["status"] == "READY" and result["publication_status"] == "PUBLISHED"
    assert result["thumbnail"] == {"status": "FAILED", "source": "NONE", "url": None}
    assert "processing_error" not in result
    assert storage.private_reads == (1 if permanent else 3)
    assert delays == ([] if permanent else [1, 4])
    assert await storage.list("public", "videos/") == []


async def test_concurrent_custom_activation_keeps_priority_and_generated_fallback(
    thumbnail_client: AsyncClient, api_app: FastAPI, test_database: tuple[str, str], tmp_path: Path
) -> None:
    storage = ControlledThumbnailStorage()
    path, job = await seed_thumbnail(
        thumbnail_client, test_database, storage, source_video(tmp_path / "source.mp4")
    )
    storage.write_started, storage.write_release = asyncio.Event(), asyncio.Event()
    execution = asyncio.create_task(run_job(job, api_app.state.database, storage, Settings()))
    await asyncio.wait_for(storage.write_started.wait(), 10)
    url, schema = test_database
    custom_key = path.removeprefix("/v1/") + "/custom.jpg"
    custom_image = tmp_path / "custom.jpg"
    subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "color=c=blue:s=1280x720:d=1",
            "-frames:v",
            "1",
            str(custom_image),
        ],
        check=True,
        capture_output=True,
    )
    storage.objects[("public", custom_key)] = custom_image.read_bytes(), "image/jpeg"

    async with await AsyncConnection.connect(url, autocommit=True) as connection:
        cursor = await connection.execute(
            sql.SQL("SELECT output_keys FROM {}.jobs WHERE id=%s").format(sql.Identifier(schema)),
            (job,),
        )
        assert await cursor.fetchone() == ([storage.pending_key],)
        await connection.execute(
            sql.SQL("UPDATE {}.videos SET custom_thumbnail_key=%s").format(sql.Identifier(schema)),
            (custom_key,),
        )
    before = (await thumbnail_client.get(path)).json()["thumbnail"]
    assert before == {
        "status": "READY",
        "source": "CUSTOM",
        "url": "https://media.example.com/" + custom_key,
    }
    storage.write_release.set()
    assert await execution
    assert (await thumbnail_client.get(path)).json()["thumbnail"] == before
    async with await AsyncConnection.connect(url, autocommit=True) as connection:
        await connection.execute(
            sql.SQL("UPDATE {}.videos SET custom_thumbnail_key=NULL").format(sql.Identifier(schema))
        )
        cursor = await connection.execute(
            sql.SQL("SELECT source_validated FROM {}.videos").format(sql.Identifier(schema))
        )
        assert await cursor.fetchone() == (False,)
    fallback = (await thumbnail_client.get(path)).json()["thumbnail"]
    assert fallback["source"] == "GENERATED"
    assert urlsplit(str(fallback["url"])).path.lstrip("/") == storage.pending_key


@pytest.mark.parametrize("fence", ["deletion", "superseded"])
async def test_late_thumbnail_execution_cannot_activate_after_fencing(
    thumbnail_client: AsyncClient,
    api_app: FastAPI,
    test_database: tuple[str, str],
    tmp_path: Path,
    fence: str,
) -> None:
    storage = ControlledThumbnailStorage()
    path, job = await seed_thumbnail(
        thumbnail_client, test_database, storage, source_video(tmp_path / "source.mp4")
    )
    storage.write_started, storage.write_release = asyncio.Event(), asyncio.Event()
    execution = asyncio.create_task(run_job(job, api_app.state.database, storage, Settings()))
    await asyncio.wait_for(storage.write_started.wait(), 10)
    url, schema = test_database
    async with await AsyncConnection.connect(url, autocommit=True) as connection:
        await connection.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(schema)))
        if fence == "deletion":
            await connection.execute("UPDATE videos SET status='DELETING'")
        else:
            await connection.execute("UPDATE jobs SET is_current=false WHERE id=%s", (job,))
            await connection.execute(
                """INSERT INTO jobs(id,video_id,kind,output_prefix,created_at,updated_at)
                SELECT %s,video_id,'THUMBNAIL',%s,now(),now() FROM jobs WHERE id=%s""",
                (uuid4(), "new-thumbnail/", job),
            )
    storage.write_release.set()
    assert not await execution
    video = (await thumbnail_client.get(path)).json()
    assert video["thumbnail"] == {"status": "PENDING", "source": "NONE", "url": None}
    assert video["status"] == ("DELETING" if fence == "deletion" else "PROCESSING")


async def test_duplicate_thumbnail_execution_cannot_steal_current_claim(
    thumbnail_client: AsyncClient, api_app: FastAPI, test_database: tuple[str, str], tmp_path: Path
) -> None:
    storage = ControlledThumbnailStorage()
    path, job = await seed_thumbnail(
        thumbnail_client, test_database, storage, source_video(tmp_path / "source.mp4")
    )
    storage.write_started, storage.write_release = asyncio.Event(), asyncio.Event()
    execution = asyncio.create_task(run_job(job, api_app.state.database, storage, Settings()))
    await asyncio.wait_for(storage.write_started.wait(), 10)
    assert not await run_job(job, api_app.state.database, storage, Settings())
    storage.write_release.set()
    assert await execution
    assert (await thumbnail_client.get(path)).json()["thumbnail"]["status"] == "READY"
    assert len(await storage.list("public", "videos/")) == 1


async def test_generated_failure_preserves_custom_image_and_video_error(
    thumbnail_client: AsyncClient,
    api_app: FastAPI,
    storage: MemoryStorage,
    test_database: tuple[str, str],
) -> None:
    path, job = await seed_thumbnail(
        thumbnail_client, test_database, storage, b"invalid MP4", status="FAILED"
    )
    url, schema = test_database
    custom = "videos/accepted-custom.jpg"
    async with await AsyncConnection.connect(url, autocommit=True) as connection:
        await connection.execute(
            sql.SQL(
                "UPDATE {}.videos SET custom_thumbnail_key=%s, source_validated=true,processing_error_code='VIDEO_FAILURE',processing_error_message='Video processing failed.'"
            ).format(sql.Identifier(schema)),
            (custom,),
        )
    assert not await run_job(job, api_app.state.database, storage, Settings())
    video = (await thumbnail_client.get(path)).json()
    assert video["status"] == "FAILED"
    assert video["thumbnail"] == {
        "status": "READY",
        "source": "CUSTOM",
        "url": "https://media.example.com/" + custom,
    }
    assert video["processing_error"] == {
        "code": "VIDEO_FAILURE",
        "message": "Video processing failed.",
    }
    async with await AsyncConnection.connect(url, autocommit=True) as connection:
        await connection.execute(
            sql.SQL("UPDATE {}.videos SET custom_thumbnail_key=NULL").format(sql.Identifier(schema))
        )
        cursor = await connection.execute(
            sql.SQL("SELECT source_validated FROM {}.videos").format(sql.Identifier(schema))
        )
        assert await cursor.fetchone() == (True,)
    assert (await thumbnail_client.get(path)).json()["thumbnail"] == {
        "status": "FAILED",
        "source": "NONE",
        "url": None,
    }


async def test_unverified_stored_image_never_activates(
    thumbnail_client: AsyncClient, api_app: FastAPI, test_database: tuple[str, str], tmp_path: Path
) -> None:
    class CorruptStoredImage(ControlledThumbnailStorage):
        async def read(self, area: StorageArea, key: str, max_bytes: int) -> bytes:
            data = await super().read(area, key, max_bytes)
            return b"\0" * len(data) if area == "public" else data

    storage = CorruptStoredImage()
    path, job = await seed_thumbnail(
        thumbnail_client,
        test_database,
        storage,
        source_video(tmp_path / "source.mp4"),
        status="READY",
    )

    async def no_wait(delay: float) -> None:
        pass

    assert not await run_job(job, api_app.state.database, storage, Settings(), sleep=no_wait)
    assert storage.private_reads == 3
    video = (await thumbnail_client.get(path)).json()
    assert video["status"] == "READY" and video["thumbnail"]["status"] == "FAILED"
