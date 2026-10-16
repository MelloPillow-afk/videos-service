"""Operator-visible exit outcomes use real HTTP, PostgreSQL and media processing."""

import asyncio
import json
import subprocess
from collections.abc import AsyncIterator
from pathlib import Path
from threading import Event
from uuid import UUID

import httpx
import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from psycopg import AsyncConnection, sql

from src.providers.storage import StorageArea, TemporaryStorageError
from src.worker import main
from tests.job_provider import RecordingLauncher
from tests.providers import LocalSigningKeys
from tests.storage_provider import MemoryStorage

pytestmark = pytest.mark.integration


@pytest_asyncio.fixture
async def cli_client(
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


async def accepted_job(
    client: AsyncClient, storage: MemoryStorage, source: bytes
) -> tuple[str, UUID]:
    draft = await client.post("/v1/videos", json={"title": "CLI outcome"})
    path = draft.headers["Location"]
    issued = await client.post(
        path + ":upload-url",
        json={"file_name": "source.mp4", "content_type": "video/mp4", "size_bytes": len(source)},
    )
    upload = issued.json()["upload"]
    await storage.browser_put(upload["url"], source, upload["headers"])
    accepted = await client.post(path + ":complete-upload", json={"upload_id": upload["upload_id"]})
    assert accepted.status_code == 202
    return path, UUID(accepted.json()["processing_job_id"])


async def test_invalid_media_exits_failed_and_reports_safe_outcome(
    cli_client: AsyncClient,
    storage: MemoryStorage,
    test_database: tuple[str, str],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path, job_id = await accepted_job(cli_client, storage, b"invalid MP4 source")
    url, schema = test_database
    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.setenv("DB_SCHEMA", schema)

    with pytest.raises(SystemExit) as exited:
        await asyncio.to_thread(main, ["run", "--job-id", str(job_id)], storage=storage)

    assert exited.value.code == 1
    output = capsys.readouterr()
    assert json.loads(output.out) == {"job_id": str(job_id), "command": "run", "outcome": "failed"}
    assert url not in output.out + output.err
    assert "Traceback" not in output.err
    assert (await cli_client.get(path)).json()["status"] == "FAILED"


async def test_duplicate_failed_job_exits_no_op_without_resetting_failure(
    cli_client: AsyncClient,
    storage: MemoryStorage,
    test_database: tuple[str, str],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path, job_id = await accepted_job(cli_client, storage, b"invalid MP4 source")
    url, schema = test_database
    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.setenv("DB_SCHEMA", schema)
    with pytest.raises(SystemExit):
        await asyncio.to_thread(main, ["run", "--job-id", str(job_id)], storage=storage)
    capsys.readouterr()

    await asyncio.to_thread(main, ["run", "--job-id", str(job_id)], storage=storage)

    assert json.loads(capsys.readouterr().out)["outcome"] == "no_op"
    assert (await cli_client.get(path)).json()["status"] == "FAILED"


async def test_valid_media_exits_success_then_duplicate_is_no_op(
    cli_client: AsyncClient,
    storage: MemoryStorage,
    test_database: tuple[str, str],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source_path = tmp_path / "valid.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            "color=c=blue:s=160x90:r=5:d=1",
            "-c:v",
            "libx264",
            "-threads",
            "2",
            "-pix_fmt",
            "yuv420p",
            str(source_path),
        ],
        check=True,
        capture_output=True,
    )
    path, job_id = await accepted_job(cli_client, storage, source_path.read_bytes())
    url, schema = test_database
    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.setenv("DB_SCHEMA", schema)

    await asyncio.to_thread(main, ["run", "--job-id", str(job_id)], storage=storage)

    assert json.loads(capsys.readouterr().out)["outcome"] == "succeeded"
    assert (await cli_client.get(path)).json()["status"] == "READY"
    await asyncio.to_thread(main, ["run", "--job-id", str(job_id)], storage=storage)
    assert json.loads(capsys.readouterr().out)["outcome"] == "no_op"


async def test_unconfirmed_manual_recovery_exits_failed(
    cli_client: AsyncClient,
    storage: MemoryStorage,
    test_database: tuple[str, str],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path, job_id = await accepted_job(cli_client, storage, b"source awaiting processing")
    url, schema = test_database
    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.setenv("DB_SCHEMA", schema)
    monkeypatch.delenv("CLOUD_RUN_JOB_RESOURCE", raising=False)

    with pytest.raises(SystemExit) as exited:
        await asyncio.to_thread(main, ["recover", "--job-id", str(job_id)])

    assert exited.value.code == 1
    output = capsys.readouterr()
    assert json.loads(output.out)["outcome"] == "failed"
    assert "Launch was not confirmed" in output.err
    assert (await cli_client.get(path)).json()["status"] == "QUEUED"


class UnavailableStorage(MemoryStorage):
    def __init__(self) -> None:
        super().__init__()
        self.read_attempts = 0

    async def read(self, area: StorageArea, key: str, max_bytes: int) -> bytes:
        self.read_attempts += 1
        raise TemporaryStorageError


async def test_exhausted_provider_retries_exit_failed_after_three_attempts(
    cli_client: AsyncClient,
    storage: MemoryStorage,
    test_database: tuple[str, str],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    unavailable = UnavailableStorage()
    unavailable.objects = storage.objects
    path, job_id = await accepted_job(cli_client, storage, b"source")
    url, schema = test_database
    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.setenv("DB_SCHEMA", schema)
    monkeypatch.setenv("MEDIA_RETRY_DELAYS_SECONDS", "[0,0.001]")

    with pytest.raises(SystemExit) as exited:
        await asyncio.to_thread(main, ["run", "--job-id", str(job_id)], storage=unavailable)

    assert exited.value.code == 1
    assert json.loads(capsys.readouterr().out)["outcome"] == "failed"
    assert unavailable.read_attempts == 3
    assert (await cli_client.get(path)).json()["status"] == "FAILED"


class InflightStorage(MemoryStorage):
    def __init__(self) -> None:
        super().__init__()
        self.started = Event()
        self.release = Event()

    async def read(self, area: StorageArea, key: str, max_bytes: int) -> bytes:
        self.started.set()
        assert await asyncio.to_thread(self.release.wait, 15)
        return await super().read(area, key, max_bytes)


async def test_deletion_fences_inflight_invalid_source_to_benign_no_op(
    cli_client: AsyncClient,
    storage: MemoryStorage,
    test_database: tuple[str, str],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    inflight = InflightStorage()
    inflight.objects = storage.objects
    path, job_id = await accepted_job(cli_client, storage, b"invalid source")
    url, schema = test_database
    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.setenv("DB_SCHEMA", schema)
    execution = asyncio.create_task(
        asyncio.to_thread(main, ["run", "--job-id", str(job_id)], storage=inflight)
    )
    try:
        assert await asyncio.to_thread(inflight.started.wait, 10)
        assert (await cli_client.delete(path)).status_code == 202
    finally:
        inflight.release.set()

    await execution

    assert json.loads(capsys.readouterr().out)["outcome"] == "no_op"
    assert (await cli_client.get(path)).json()["status"] == "DELETING"


async def test_cleanup_exits_success_and_completed_duplicate_is_no_op(
    cli_client: AsyncClient,
    storage: MemoryStorage,
    launcher: RecordingLauncher,
    test_database: tuple[str, str],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    created = await cli_client.post("/v1/videos", json={"title": "Delete CLI"})
    path = created.headers["Location"]
    assert (await cli_client.delete(path)).status_code == 202
    job_id = launcher.submissions[-1]
    url, schema = test_database
    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.setenv("DB_SCHEMA", schema)

    await asyncio.to_thread(main, ["run", "--job-id", str(job_id)], storage=storage)

    assert json.loads(capsys.readouterr().out)["outcome"] == "succeeded"
    assert (await cli_client.get(path)).status_code == 404
    await asyncio.to_thread(main, ["run", "--job-id", str(job_id)], storage=storage)
    assert json.loads(capsys.readouterr().out)["outcome"] == "no_op"


class UnavailableGuards(MemoryStorage):
    async def seal(self, area: StorageArea, key: str) -> None:
        raise TemporaryStorageError


async def test_cleanup_runtime_exhaustion_exits_failed_and_stays_deleting(
    cli_client: AsyncClient,
    launcher: RecordingLauncher,
    test_database: tuple[str, str],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    created = await cli_client.post("/v1/videos", json={"title": "Guard outage"})
    path = created.headers["Location"]
    assert (
        await cli_client.post(
            path + ":upload-url",
            json={
                "file_name": "source.mp4",
                "content_type": "video/mp4",
                "size_bytes": 12,
            },
        )
    ).status_code == 200
    assert (await cli_client.delete(path)).status_code == 202
    job_id = launcher.submissions[-1]
    url, schema = test_database
    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.setenv("DB_SCHEMA", schema)
    monkeypatch.setenv("CLEANUP_RUNTIME_SECONDS", "0.1")
    monkeypatch.setenv("CLEANUP_RETRY_DELAYS_SECONDS", "[0,0.001]")

    with pytest.raises(SystemExit) as exited:
        await asyncio.to_thread(main, ["run", "--job-id", str(job_id)], storage=UnavailableGuards())

    assert exited.value.code == 1
    assert json.loads(capsys.readouterr().out)["outcome"] == "failed"
    assert (await cli_client.get(path)).json()["status"] == "DELETING"


@pytest.mark.parametrize("auth_available", [True, False])
async def test_local_gcloud_recovery_records_confirmed_or_failed_launch_through_real_cli_and_database(
    cli_client: AsyncClient,
    storage: MemoryStorage,
    test_database: tuple[str, str],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    gcloud_cli: Path,
    auth_available: bool,
) -> None:
    path, job_id = await accepted_job(cli_client, storage, b"awaiting independent media job")
    url, schema = test_database
    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.setenv("DB_SCHEMA", schema)
    monkeypatch.setenv("CLOUD_RUN_JOB_RESOURCE", "projects/target/locations/region/jobs/media")
    if not auth_available:
        monkeypatch.setenv("TEST_GCLOUD_EXIT", "1")
    requests: list[httpx.Request] = []

    async def launch(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        assert request.method == "POST" and request.url.host == "run.googleapis.com"
        assert request.headers["Authorization"] == "Bearer controlled-operator-access-token"
        assert json.loads(request.content)["overrides"]["containerOverrides"][0]["args"] == [
            "run",
            "--job-id",
            str(job_id),
        ]
        return httpx.Response(
            200, json={"name": "projects/target/locations/region/operations/operator-recovery"}
        )

    async def recover() -> None:
        await asyncio.to_thread(
            main,
            ["recover", "--job-id", str(job_id), "--gcloud-auth"],
            job_transport=httpx.MockTransport(launch),
        )

    if auth_available:
        await recover()
    else:
        with pytest.raises(SystemExit) as error:
            await recover()
        assert error.value.code == 1
    output = capsys.readouterr()
    assert json.loads(output.out) == {
        "job_id": str(job_id),
        "command": "recover",
        "outcome": "succeeded" if auth_available else "failed",
    }
    assert "controlled-operator-access-token" not in output.out + output.err
    assert "controlled-gcloud-private-error" not in output.out + output.err
    assert len(requests) == (1 if auth_available else 0) and gcloud_cli.exists()
    assert (await cli_client.get(path)).json()["status"] == "QUEUED"
    async with await AsyncConnection.connect(url) as connection:
        row = await (
            await connection.execute(
                sql.SQL(
                    "SELECT state,execution_reference,execution_attempts FROM {}.jobs WHERE id=%s"
                ).format(sql.Identifier(schema)),
                (job_id,),
            )
        ).fetchone()
    assert row == (
        ("LAUNCHED", "projects/target/locations/region/operations/operator-recovery", 0)
        if auth_available
        else ("LAUNCH_FAILED", f"projects/test/locations/test/operations/{job_id}", 0)
    )
