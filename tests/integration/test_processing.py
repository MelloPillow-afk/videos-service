"""HTTP-visible worker outcomes using PostgreSQL and real FFmpeg media."""

import json
import subprocess
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from psycopg import AsyncConnection, sql

from src.config import Settings
from src.providers.storage import StorageLimitError, StoredObject, UploadInstructions
from src.worker import run_job
from tests.providers import LocalSigningKeys

pytestmark = pytest.mark.integration


class MediaStorage:
    def __init__(self) -> None:
        self.objects: dict[tuple[str, str], bytes] = {}
        self.drop_segments = False

    async def read(self, area: str, key: str, max_bytes: int) -> bytes:
        data = self.objects[(area, key)]
        if len(data) > max_bytes:
            raise StorageLimitError
        return data

    async def head(self, area: str, key: str) -> StoredObject | None:
        data = self.objects.get((area, key))
        return StoredObject(len(data), "application/octet-stream") if data is not None else None

    async def write(
        self, area: str, key: str, data: bytes, content_type: str, *, create_only: bool = True
    ) -> None:
        assert create_only, "ordinary workers must never overwrite objects"
        assert (area, key) not in self.objects
        if not (self.drop_segments and key.endswith(".ts")):
            self.objects[(area, key)] = data

    async def list(self, area: str, prefix: str) -> list[str]:
        return [
            key for found_area, key in self.objects if found_area == area and key.startswith(prefix)
        ]

    async def delete(self, area: str, key: str) -> None:
        self.objects.pop((area, key), None)

    async def sign_upload(
        self, key: str, content_type: str, expires_seconds: int = 900
    ) -> UploadInstructions:
        return UploadInstructions("https://uploads.test/" + key, {"If-None-Match": "*"})


@pytest_asyncio.fixture
async def worker_client(api_app: FastAPI) -> AsyncIterator[AsyncClient]:
    async with (
        api_app.router.lifespan_context(api_app),
        AsyncClient(transport=ASGITransport(app=api_app), base_url="http://test") as client,
    ):
        yield client


def make_source(path: Path, size: str = "320x180", duration: str = "1") -> bytes:
    subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"testsrc2=size={size}:rate=10:duration={duration}",
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


async def seed_job(
    client: AsyncClient,
    signing_keys: LocalSigningKeys,
    test_database: tuple[str, str],
    storage: MediaStorage,
    source: bytes,
) -> tuple[str, UUID]:
    response = await client.post(
        "/v1/videos",
        json={"title": "Real media"},
        headers={"Authorization": "Bearer " + signing_keys.token()},
    )
    assert response.status_code == 201
    video_id = response.json()["id"]
    job_id = uuid4()
    source_key = f"videos/{video_id}/source.mp4"
    storage.objects[("private", source_key)] = source
    url, schema = test_database
    async with await AsyncConnection.connect(url, autocommit=True) as connection:
        await connection.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(schema)))
        await connection.execute(
            "UPDATE videos SET status='QUEUED',source_key=%s,size_bytes=%s WHERE id=%s",
            (source_key, len(source), video_id),
        )
        await connection.execute(
            """INSERT INTO jobs(id,video_id,kind,output_prefix,created_at,updated_at)
            VALUES (%s,%s,'VIDEO',%s,%s,%s)""",
            (
                job_id,
                video_id,
                f"videos/{video_id}/jobs/{job_id}",
                datetime.now(UTC),
                datetime.now(UTC),
            ),
        )
    return response.headers["Location"], job_id


async def test_accepted_source_becomes_playable_without_publishing(
    worker_client: AsyncClient,
    api_app: FastAPI,
    signing_keys: LocalSigningKeys,
    test_database: tuple[str, str],
    tmp_path: Path,
) -> None:
    storage = MediaStorage()
    source = make_source(tmp_path / "source.mp4")
    location, job_id = await seed_job(worker_client, signing_keys, test_database, storage, source)

    await run_job(job_id, api_app.state.database, storage, Settings())

    response = await worker_client.get(
        location, headers={"Authorization": "Bearer " + signing_keys.token()}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "READY"
    assert response.json()["publication_status"] == "DRAFT"
    assert response.json()["duration_seconds"] == 1
    assert (await worker_client.get(location)).status_code == 404
    master_keys = [
        key for area, key in storage.objects if area == "public" and key.endswith("master.m3u8")
    ]
    assert len(master_keys) == 1
    master = storage.objects[("public", master_keys[0])].decode()
    assert "RESOLUTION=320x180" in master
    assert any(area == "private" and data == source for (area, _), data in storage.objects.items())
    public = tmp_path / "public"
    public.mkdir()
    prefix = master_keys[0].rsplit("/", 1)[0]
    for (area, key), data in storage.objects.items():
        if area == "public":
            target = public / key.removeprefix(prefix + "/")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
    subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(public / "master.m3u8"), "-f", "null", "-"],
        check=True,
        capture_output=True,
    )
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_streams", "-of", "json", str(public / "master.m3u8")],
        check=True,
        capture_output=True,
        text=True,
    )
    assert json.loads(probe.stdout)["streams"][0]["codec_name"] == "h264"


async def test_corrupt_source_fails_with_safe_administrator_explanation(
    worker_client: AsyncClient,
    api_app: FastAPI,
    signing_keys: LocalSigningKeys,
    test_database: tuple[str, str],
) -> None:
    storage = MediaStorage()
    location, job_id = await seed_job(
        worker_client, signing_keys, test_database, storage, b"not an mp4 secret-source-location"
    )

    assert not await run_job(job_id, api_app.state.database, storage, Settings())

    response = await worker_client.get(
        location, headers={"Authorization": "Bearer " + signing_keys.token()}
    )
    assert response.json()["status"] == "FAILED"
    assert response.json()["processing_error"] == {
        "code": "INVALID_SOURCE",
        "message": "The source is corrupt or unsupported MP4 media.",
    }
    assert not any(area == "public" for area, _ in storage.objects)


@pytest.mark.parametrize(
    "size,expected",
    [
        ("1920x1080", ["640x360", "1280x720", "1920x1080"]),
        ("720x1280", ["360x640", "720x1280"]),
        ("640x480", ["480x360"]),
    ],
)
async def test_supported_renditions_preserve_proportions_without_upscaling(
    worker_client: AsyncClient,
    api_app: FastAPI,
    signing_keys: LocalSigningKeys,
    test_database: tuple[str, str],
    tmp_path: Path,
    size: str,
    expected: list[str],
) -> None:
    storage = MediaStorage()
    location, job_id = await seed_job(
        worker_client,
        signing_keys,
        test_database,
        storage,
        make_source(tmp_path / "source.mp4", size),
    )
    assert await run_job(job_id, api_app.state.database, storage, Settings())
    master = next(
        data.decode()
        for (area, key), data in storage.objects.items()
        if area == "public" and key.endswith("master.m3u8")
    )
    assert [
        line.split("RESOLUTION=")[1] for line in master.splitlines() if "RESOLUTION=" in line
    ] == expected
    assert (
        await worker_client.get(
            location, headers={"Authorization": "Bearer " + signing_keys.token()}
        )
    ).json()["status"] == "READY"


@pytest.mark.parametrize("duration,status", [("300", "READY"), ("300.1", "FAILED")])
async def test_actual_five_minute_boundary(
    worker_client: AsyncClient,
    api_app: FastAPI,
    signing_keys: LocalSigningKeys,
    test_database: tuple[str, str],
    tmp_path: Path,
    duration: str,
    status: str,
) -> None:
    storage = MediaStorage()
    location, job_id = await seed_job(
        worker_client,
        signing_keys,
        test_database,
        storage,
        make_source(tmp_path / "source.mp4", "16x16", duration),
    )
    await run_job(job_id, api_app.state.database, storage, Settings())
    response = await worker_client.get(
        location, headers={"Authorization": "Bearer " + signing_keys.token()}
    )
    assert response.json()["status"] == status
    if status == "FAILED":
        assert response.json()["processing_error"]["code"] == "INVALID_SOURCE"
        assert not any(area == "public" for area, _ in storage.objects)


async def test_missing_published_asset_cannot_become_ready(
    worker_client: AsyncClient,
    api_app: FastAPI,
    signing_keys: LocalSigningKeys,
    test_database: tuple[str, str],
    tmp_path: Path,
) -> None:
    storage = MediaStorage()
    storage.drop_segments = True
    location, job_id = await seed_job(
        worker_client, signing_keys, test_database, storage, make_source(tmp_path / "source.mp4")
    )
    assert not await run_job(job_id, api_app.state.database, storage, Settings())
    response = await worker_client.get(
        location, headers={"Authorization": "Bearer " + signing_keys.token()}
    )
    assert response.json()["status"] == "FAILED"
    assert response.json()["processing_error"]["code"] == "PROCESSING_FAILED"


async def test_duplicate_worker_invocations_claim_once(
    worker_client: AsyncClient,
    api_app: FastAPI,
    signing_keys: LocalSigningKeys,
    test_database: tuple[str, str],
    tmp_path: Path,
) -> None:
    import asyncio

    storage = MediaStorage()
    location, job_id = await seed_job(
        worker_client, signing_keys, test_database, storage, make_source(tmp_path / "source.mp4")
    )
    results = await asyncio.gather(
        *(run_job(job_id, api_app.state.database, storage, Settings()) for _ in range(2))
    )
    assert sorted(results) == [False, True]
    assert (
        await worker_client.get(
            location, headers={"Authorization": "Bearer " + signing_keys.token()}
        )
    ).json()["status"] == "READY"
    async with await AsyncConnection.connect(test_database[0]) as connection:
        cursor = await connection.execute(
            sql.SQL("SELECT execution_attempts FROM {}.jobs WHERE id=%s").format(
                sql.Identifier(test_database[1])
            ),
            (job_id,),
        )
        assert await cursor.fetchone() == (1,)


async def test_manifest_is_persisted_before_output_write_and_deletion_fences_result(
    worker_client: AsyncClient,
    api_app: FastAPI,
    signing_keys: LocalSigningKeys,
    test_database: tuple[str, str],
    tmp_path: Path,
) -> None:
    class DeleteDuringWrite(MediaStorage):
        manifest: list[str] = []

        async def write(
            self, area: str, key: str, data: bytes, content_type: str, *, create_only: bool = True
        ) -> None:
            async with await AsyncConnection.connect(
                test_database[0], autocommit=True
            ) as connection:
                cursor = await connection.execute(
                    sql.SQL("SELECT output_keys FROM {}.jobs WHERE id=%s").format(
                        sql.Identifier(test_database[1])
                    ),
                    (job_id,),
                )
                row = await cursor.fetchone()
                assert row is not None
                self.manifest = row[0]
                assert key in self.manifest and any(
                    value.endswith("master.m3u8") for value in self.manifest
                )
                await connection.execute(
                    sql.SQL("UPDATE {}.videos SET status='DELETING'").format(
                        sql.Identifier(test_database[1])
                    )
                )
            await super().write(area, key, data, content_type, create_only=create_only)

    storage = DeleteDuringWrite()
    location, job_id = await seed_job(
        worker_client, signing_keys, test_database, storage, make_source(tmp_path / "source.mp4")
    )
    assert not await run_job(job_id, api_app.state.database, storage, Settings())
    response = await worker_client.get(
        location, headers={"Authorization": "Bearer " + signing_keys.token()}
    )
    assert response.json()["status"] == "DELETING"
    assert len([1 for area, _ in storage.objects if area == "public"]) == 1
    assert not any(key.endswith("master.m3u8") for area, key in storage.objects if area == "public")


async def test_encoder_runtime_timeout_is_not_a_permanent_source_rejection(
    worker_client: AsyncClient,
    api_app: FastAPI,
    signing_keys: LocalSigningKeys,
    test_database: tuple[str, str],
    tmp_path: Path,
) -> None:
    storage = MediaStorage()
    location, job_id = await seed_job(
        worker_client, signing_keys, test_database, storage, make_source(tmp_path / "source.mp4")
    )
    assert not await run_job(
        job_id, api_app.state.database, storage, Settings(media_encode_timeout_seconds=0.000001)
    )
    response = await worker_client.get(
        location, headers={"Authorization": "Bearer " + signing_keys.token()}
    )
    assert response.json()["processing_error"]["code"] == "PROCESSING_FAILED"


@pytest.mark.parametrize("mode,expected", [("sar", "320x120"), ("rotation", "180x320")])
async def test_sample_aspect_and_rotation_preserve_displayed_proportions(
    worker_client: AsyncClient,
    api_app: FastAPI,
    signing_keys: LocalSigningKeys,
    test_database: tuple[str, str],
    tmp_path: Path,
    mode: str,
    expected: str,
) -> None:
    input_path = tmp_path / "input.mp4"
    make_source(input_path, "320x240" if mode == "sar" else "320x180")
    source_path = tmp_path / "adjusted.mp4"
    arguments = ["ffmpeg", "-v", "error", "-y"]
    if mode == "rotation":
        arguments += ["-display_rotation:v:0", "90"]
    arguments += ["-i", str(input_path)]
    if mode == "sar":
        arguments += ["-vf", "setsar=2", "-c:v", "libx264", "-threads", "2"]
    else:
        arguments += ["-c", "copy", "-metadata:s:v:0", "rotate=90"]
    subprocess.run(arguments + [str(source_path)], check=True, capture_output=True)
    storage = MediaStorage()
    _, job_id = await seed_job(
        worker_client, signing_keys, test_database, storage, source_path.read_bytes()
    )
    assert await run_job(job_id, api_app.state.database, storage, Settings())
    master = next(
        data.decode()
        for (area, key), data in storage.objects.items()
        if area == "public" and key.endswith("master.m3u8")
    )
    assert "RESOLUTION=" + expected in master


async def test_audio_is_encoded_as_stereo_aac_and_hls_is_decodable(
    worker_client: AsyncClient,
    api_app: FastAPI,
    signing_keys: LocalSigningKeys,
    test_database: tuple[str, str],
    tmp_path: Path,
) -> None:
    source_path = tmp_path / "audio.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "testsrc2=size=320x180:rate=10:duration=1",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:sample_rate=44100:duration=1",
            "-c:v",
            "libx264",
            "-threads",
            "2",
            "-c:a",
            "aac",
            str(source_path),
        ],
        check=True,
        capture_output=True,
    )
    storage = MediaStorage()
    _, job_id = await seed_job(
        worker_client, signing_keys, test_database, storage, source_path.read_bytes()
    )
    assert await run_job(job_id, api_app.state.database, storage, Settings())
    for (area, key), data in storage.objects.items():
        if area == "public":
            (tmp_path / key.rsplit("/", 1)[1]).write_bytes(data)
    playlist = str(tmp_path / "master.m3u8")
    subprocess.run(
        ["ffmpeg", "-v", "error", "-i", playlist, "-f", "null", "-"],
        check=True,
        capture_output=True,
    )
    probed = subprocess.run(
        ["ffprobe", "-v", "error", "-show_streams", "-of", "json", playlist],
        check=True,
        capture_output=True,
        text=True,
    )
    audio = next(
        stream for stream in json.loads(probed.stdout)["streams"] if stream["codec_type"] == "audio"
    )
    assert (audio["codec_name"], audio["sample_rate"], audio["channels"]) == ("aac", "48000", 2)


async def test_unsupported_actual_container_is_rejected_despite_mp4_name(
    worker_client: AsyncClient,
    api_app: FastAPI,
    signing_keys: LocalSigningKeys,
    test_database: tuple[str, str],
    tmp_path: Path,
) -> None:
    source_path = tmp_path / "source.webm"
    subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "testsrc2=size=16x16:rate=10:duration=1",
            "-c:v",
            "libvpx",
            str(source_path),
        ],
        check=True,
        capture_output=True,
    )
    storage = MediaStorage()
    location, job_id = await seed_job(
        worker_client, signing_keys, test_database, storage, source_path.read_bytes()
    )
    assert not await run_job(job_id, api_app.state.database, storage, Settings())
    response = await worker_client.get(
        location, headers={"Authorization": "Bearer " + signing_keys.token()}
    )
    assert response.json()["processing_error"]["code"] == "INVALID_SOURCE"
    assert not any(area == "public" for area, _ in storage.objects)


async def test_superseded_job_cannot_commit_ready_after_upload(
    worker_client: AsyncClient,
    api_app: FastAPI,
    signing_keys: LocalSigningKeys,
    test_database: tuple[str, str],
    tmp_path: Path,
) -> None:
    class SupersedeAfterUpload(MediaStorage):
        async def head(self, area: str, key: str) -> StoredObject | None:
            if area == "public" and key.endswith("master.m3u8"):
                async with await AsyncConnection.connect(
                    test_database[0], autocommit=True
                ) as connection:
                    await connection.execute(
                        sql.SQL("UPDATE {}.jobs SET is_current=false WHERE id=%s").format(
                            sql.Identifier(test_database[1])
                        ),
                        (job_id,),
                    )
            return await super().head(area, key)

    storage = SupersedeAfterUpload()
    location, job_id = await seed_job(
        worker_client, signing_keys, test_database, storage, make_source(tmp_path / "source.mp4")
    )
    assert not await run_job(job_id, api_app.state.database, storage, Settings())
    response = await worker_client.get(
        location, headers={"Authorization": "Bearer " + signing_keys.token()}
    )
    assert response.json()["status"] == "PROCESSING"
    assert (await worker_client.get(location)).status_code == 404


async def test_corrupt_video_packets_fail_even_when_mp4_metadata_is_valid(
    worker_client: AsyncClient,
    api_app: FastAPI,
    signing_keys: LocalSigningKeys,
    test_database: tuple[str, str],
    tmp_path: Path,
) -> None:
    source = bytearray(make_source(tmp_path / "source.mp4"))
    marker = source.index(b"mdat")
    atom_size = int.from_bytes(source[marker - 4 : marker], "big")
    source[marker + 4 : marker - 4 + atom_size] = bytes(atom_size - 8)
    storage = MediaStorage()
    location, job_id = await seed_job(
        worker_client, signing_keys, test_database, storage, bytes(source)
    )
    assert not await run_job(job_id, api_app.state.database, storage, Settings())
    response = await worker_client.get(
        location, headers={"Authorization": "Bearer " + signing_keys.token()}
    )
    assert response.json()["status"] == "FAILED"
    assert response.json()["processing_error"]["code"] == "INVALID_SOURCE"
    assert not any(area == "public" for area, _ in storage.objects)
