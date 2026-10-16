"""Deletion acceptance fences real application state before physical cleanup."""

import asyncio
import json
import os
import sys
from asyncio import Event, create_subprocess_exec, create_task, gather, wait_for
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from psycopg import AsyncConnection, sql
from psycopg.types.json import Jsonb

from src.config import Settings
from src.domain.videos import VideoConflict
from src.providers.storage import StorageArea, StorageConflictError, TemporaryStorageError
from src.services.job_recovery import JobSubmission
from src.worker import run_job
from tests.integration.test_custom_thumbnails import image_bytes
from tests.integration.test_processing import make_source
from tests.job_provider import RecordingLauncher
from tests.providers import LocalSigningKeys
from tests.storage_provider import MemoryStorage

pytestmark = pytest.mark.integration


@pytest_asyncio.fixture
async def deletion_client(
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


async def test_deletion_records_one_cleanup_job_and_immediately_hides_published_media(
    deletion_client: AsyncClient,
    test_database: tuple[str, str],
    launcher: RecordingLauncher,
    api_app: FastAPI,
) -> None:
    created = await deletion_client.post("/v1/videos", json={"title": "Delete me"})
    path, id = created.headers["Location"], created.json()["id"]
    url, schema = test_database
    async with await AsyncConnection.connect(url, autocommit=True) as connection:
        await connection.execute(
            sql.SQL(
                "UPDATE {}.videos SET status='READY',publication_status='PUBLISHED',published_at=now(),playback_key='video/master.m3u8' WHERE id=%s"
            ).format(sql.Identifier(schema)),
            (id,),
        )
    assert (await deletion_client.get(path, headers={"Authorization": ""})).status_code == 401
    deleted = await deletion_client.delete(path)
    assert deleted.status_code == 202
    assert deleted.json() == {"video_id": id, "status": "DELETING"}
    repetitions = await gather(*(deletion_client.delete(path) for _ in range(2)))
    assert all(response.status_code == 202 for response in repetitions)
    assert (await deletion_client.get(path)).json()["status"] == "DELETING"
    async with AsyncClient(transport=ASGITransport(app=api_app), base_url="http://test") as viewer:
        assert (await viewer.get(path)).status_code == 404
        assert (await viewer.get(path + "/playback")).status_code == 404
        assert (await viewer.get("/v1/videos")).json()["data"] == []
    assert (await deletion_client.get(path + "/playback")).status_code == 404
    async with await AsyncConnection.connect(url, autocommit=True) as connection:
        rows = await (
            await connection.execute(
                sql.SQL(
                    "SELECT id,state,execution_reference,error_code FROM {}.jobs WHERE video_id=%s AND kind='DELETION'"
                ).format(sql.Identifier(schema)),
                (id,),
            )
        ).fetchall()
    assert len(rows) == 1 and rows[0][1] == "LAUNCHED"
    assert rows[0][2] and rows[0][3] is None
    assert launcher.submissions == [UUID(rows[0][0].hex)]


async def test_cleanup_guards_registered_and_listed_keys_then_removes_all_application_rows(
    deletion_client: AsyncClient,
    api_app: FastAPI,
    test_database: tuple[str, str],
    launcher: RecordingLauncher,
    storage: MemoryStorage,
) -> None:
    created = await deletion_client.post("/v1/videos", json={"title": "Guard deletion"})
    path, video_id = created.headers["Location"], created.json()["id"]
    source = await deletion_client.post(
        path + ":upload-url",
        json={
            "file_name": "source.mp4",
            "content_type": "video/mp4",
            "size_bytes": 12,
        },
    )
    upload = source.json()["upload"]
    private_upload = unquote(urlsplit(str(upload["url"])).path.lstrip("/"))
    prefix = f"videos/{video_id}/"
    absent_output = prefix + "jobs/old/attempt-2/late.ts"
    known_output = prefix + "jobs/old/attempt-1/old.ts"
    listed_orphan = prefix + "unregistered-legacy.jpg"
    await storage.write("private", "legacy/original.mp4", b"source", "video/mp4")
    await storage.write("public", known_output, b"segment", "video/mp2t")
    await storage.write("public", listed_orphan, b"old image", "image/jpeg")
    url, schema = test_database
    async with await AsyncConnection.connect(url, autocommit=True) as connection:
        await connection.execute(
            sql.SQL(
                "UPDATE {}.videos SET source_key='legacy/original.mp4',playback_key=%s WHERE id=%s"
            ).format(sql.Identifier(schema)),
            (known_output, video_id),
        )
        await connection.execute(
            sql.SQL(
                "INSERT INTO {}.jobs (id,video_id,kind,is_current,output_prefix,output_keys,created_at,updated_at) VALUES (%s,%s,'VIDEO',false,%s,%s,now(),now())"
            ).format(sql.Identifier(schema)),
            (uuid4(), video_id, prefix + "jobs/old/", Jsonb([known_output, absent_output])),
        )
    assert (await deletion_client.delete(path)).status_code == 202
    job = launcher.submissions[0]
    results = await gather(
        *(run_job(job, api_app.state.database, storage, Settings()) for _ in range(2))
    )
    assert results.count(True) == 1 and results.count(None) == 1
    assert (await deletion_client.get(path)).status_code == 404
    assert (await deletion_client.delete(path)).status_code == 404
    expected: set[tuple[StorageArea, str]] = {
        ("private", private_upload),
        ("private", "legacy/original.mp4"),
        ("public", known_output),
        ("public", absent_output),
        ("public", listed_orphan),
    }
    assert set(storage.objects) == expected
    for area, key in expected:
        observed = await storage.head(area, key)
        assert observed is not None and observed.size_bytes == 0 and observed.deletion_guard
        assert await storage.read(area, key, 1) == b""
    with pytest.raises(StorageConflictError):
        await storage.browser_put(upload["url"], b"source bytes", upload["headers"])
    with pytest.raises(StorageConflictError):
        await storage.write("public", absent_output, b"late media", "video/mp2t", create_only=True)
    async with await AsyncConnection.connect(url, autocommit=True) as connection:
        for table in ("videos", "jobs", "upload_attempts"):
            count = await (
                await connection.execute(
                    sql.SQL("SELECT count(*) FROM {}.{}").format(
                        sql.Identifier(schema), sql.Identifier(table)
                    )
                )
            ).fetchone()
            assert count == (0,)


async def test_failed_cleanup_launch_stays_visible_and_repeat_does_not_launch_again(
    deletion_client: AsyncClient,
    test_database: tuple[str, str],
    launcher: RecordingLauncher,
) -> None:
    created = await deletion_client.post("/v1/videos", json={"title": "Launch failure"})
    path = created.headers["Location"]
    launcher.fail = True
    assert (await deletion_client.delete(path)).status_code == 202
    assert (await deletion_client.delete(path)).status_code == 202
    assert len(launcher.submissions) == 1
    url, schema = test_database
    async with await AsyncConnection.connect(url, autocommit=True) as connection:
        row = await (
            await connection.execute(
                sql.SQL(
                    "SELECT j.state,j.error_code,j.error_message,v.status FROM {}.jobs j JOIN {}.videos v ON v.id=j.video_id WHERE j.id=%s"
                ).format(sql.Identifier(schema), sql.Identifier(schema)),
                (launcher.submissions[0],),
            )
        ).fetchone()
    assert row is not None and row[0:2] == ("LAUNCH_FAILED", "LAUNCH_UNCONFIRMED")
    assert "inspect executions" in row[2] and row[3] == "DELETING"


async def test_deletion_rejects_all_implemented_mutations_and_late_source_acceptance(
    deletion_client: AsyncClient,
    storage: MemoryStorage,
    test_database: tuple[str, str],
) -> None:
    created = await deletion_client.post("/v1/videos", json={"title": "Fence uploads"})
    path = created.headers["Location"]
    source = await deletion_client.post(
        path + ":upload-url",
        json={
            "file_name": "source.mp4",
            "content_type": "video/mp4",
            "size_bytes": 12,
        },
    )
    assert source.status_code == 200
    upload = source.json()["upload"]
    await storage.browser_put(upload["url"], b"source bytes", upload["headers"])
    storage.head_started, storage.head_release = Event(), Event()
    accepting = create_task(
        deletion_client.post(path + ":complete-upload", json={"upload_id": upload["upload_id"]})
    )
    await wait_for(storage.head_started.wait(), timeout=3)
    try:
        assert (await deletion_client.delete(path)).status_code == 202
    finally:
        storage.head_release.set()
    assert (await wait_for(accepting, timeout=3)).status_code == 409
    requests = [
        ("PATCH", path, {"title": "Cannot mutate"}),
        (
            "POST",
            path + ":upload-url",
            {"file_name": "source.mp4", "content_type": "video/mp4", "size_bytes": 12},
        ),
        ("POST", path + ":complete-upload", {"upload_id": upload["upload_id"]}),
        (
            "POST",
            path + "/thumbnails:upload-url",
            {"file_name": "cover.jpg", "content_type": "image/jpeg", "size_bytes": 12},
        ),
        ("POST", path + "/thumbnails:complete-upload", {"upload_id": upload["upload_id"]}),
        ("DELETE", path + "/thumbnails", None),
    ]
    for method, endpoint, body in requests:
        assert (await deletion_client.request(method, endpoint, json=body)).status_code == 409
    url, schema = test_database
    async with await AsyncConnection.connect(url, autocommit=True) as connection:
        assert await (
            await connection.execute(
                sql.SQL("SELECT kind FROM {}.jobs WHERE video_id=%s").format(
                    sql.Identifier(schema)
                ),
                (created.json()["id"],),
            )
        ).fetchall() == [("DELETION",)]


async def test_current_role_is_required_and_missing_deletion_returns_404(
    deletion_client: AsyncClient,
    api_app: FastAPI,
    test_database: tuple[str, str],
) -> None:
    created = await deletion_client.post("/v1/videos", json={"title": "Permission"})
    path = created.headers["Location"]
    async with AsyncClient(transport=ASGITransport(app=api_app), base_url="http://test") as viewer:
        assert (await viewer.delete(path)).status_code == 401
    assert (
        await deletion_client.delete("/v1/videos/550e8400-e29b-41d4-a716-446655440001")
    ).status_code == 404
    url, schema = test_database
    async with await AsyncConnection.connect(url, autocommit=True) as connection:
        await connection.execute(
            sql.SQL("UPDATE {}.\"user\" SET role='user'").format(sql.Identifier(schema + "_auth"))
        )
    assert (await deletion_client.delete(path)).status_code == 403


async def test_readonly_inventory_keeps_all_attempts_keys_job_manifests_and_writer_history(
    deletion_client: AsyncClient,
    test_database: tuple[str, str],
    launcher: RecordingLauncher,
) -> None:
    created = await deletion_client.post("/v1/videos", json={"title": "Inspect deletion"})
    path, id = created.headers["Location"], created.json()["id"]
    url, schema = test_database
    async with await AsyncConnection.connect(url, autocommit=True) as connection:
        await connection.execute(
            sql.SQL(
                "UPDATE {}.videos SET source_key='legacy/original.mp4',playback_key='legacy/master.m3u8',generated_thumbnail_key='legacy/generated.jpg',custom_thumbnail_key='legacy/custom.jpg' WHERE id=%s"
            ).format(sql.Identifier(schema)),
            (id,),
        )
        for n, state in [(1, "SUPERSEDED"), (2, "REMOVED"), (3, "PENDING")]:
            await connection.execute(
                sql.SQL(
                    "INSERT INTO {}.upload_attempts (id,video_id,kind,object_key,public_object_key,declared_size_bytes,content_type,expires_at,created_at,state,is_current) VALUES (%s,%s,'THUMBNAIL',%s,%s,100,'image/jpeg',now()+interval '15 minutes',now(),%s,false)"
                ).format(sql.Identifier(schema)),
                (UUID(int=n), id, f"private/upload-{n}", f"public/copy-{n}", state),
            )
        await connection.execute(
            sql.SQL(
                "INSERT INTO {}.jobs (id,video_id,kind,state,is_current,output_prefix,output_keys,execution_reference,created_at,updated_at) VALUES (%s,%s,'VIDEO','RUNNING',false,'legacy/job/','[\"legacy/attempt-1/a.ts\",\"legacy/attempt-2/b.ts\"]','projects/test/operations/in-flight',now(),now())"
            ).format(sql.Identifier(schema)),
            (UUID(int=10), id),
        )
    assert (await deletion_client.delete(path)).status_code == 202
    job = launcher.submissions[0]
    process = await create_subprocess_exec(
        sys.executable,
        "-m",
        "src.cleanup",
        "inspect",
        "--job-id",
        str(job),
        env={**os.environ, "DATABASE_URL": url, "DB_SCHEMA": schema, "DB_POOL_MIN_SIZE": "0"},
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await wait_for(process.communicate(), timeout=10)
    assert process.returncode == 0, stderr.decode()
    inventory = json.loads(stdout)
    assert inventory["private_keys"] == [
        "legacy/original.mp4",
        "private/upload-1",
        "private/upload-2",
        "private/upload-3",
    ]
    assert inventory["public_keys"] == [
        "legacy/attempt-1/a.ts",
        "legacy/attempt-2/b.ts",
        "legacy/custom.jpg",
        "legacy/generated.jpg",
        "legacy/master.m3u8",
        "public/copy-1",
        "public/copy-2",
        "public/copy-3",
    ]
    assert "legacy/job/" in inventory["prefixes"] and f"videos/{id}/" in inventory["prefixes"]
    assert {attempt["state"] for attempt in inventory["uploads"]} == {
        "SUPERSEDED",
        "REMOVED",
        "PENDING",
    }
    assert any(
        worker["state"] == "RUNNING" and worker["execution_reference"]
        for worker in inventory["workers"]
    )
    assert not inventory["storage_listed"] and not inventory["physical_cleanup_complete"]
    assert (await deletion_client.get(path)).json()["status"] == "DELETING"


class GuardTestStorage(MemoryStorage):
    def __init__(self) -> None:
        super().__init__()
        self.seal_failures = 0
        self.bad_metadata = False
        self.write_started: Event | None = None
        self.write_release: Event | None = None

    async def seal(self, area: StorageArea, key: str) -> None:
        if self.seal_failures:
            self.seal_failures -= 1
            raise TemporaryStorageError("secret provider error must stay private")
        await super().seal(area, key)
        if self.bad_metadata:
            self.guards.discard((area, key))

    async def write(
        self,
        area: StorageArea,
        key: str,
        data: bytes,
        content_type: str,
        *,
        create_only: bool = True,
    ) -> None:
        if area == "public" and self.write_started is not None and self.write_release is not None:
            self.write_started.set()
            await self.write_release.wait()
        await super().write(area, key, data, content_type, create_only=create_only)


@pytest.fixture
def storage() -> GuardTestStorage:
    return GuardTestStorage()


async def create_reserved_source(client: AsyncClient) -> tuple[str, dict[str, Any]]:
    created = await client.post("/v1/videos", json={"title": "Cleanup failure"})
    path = created.headers["Location"]
    issued = await client.post(
        path + ":upload-url",
        json={
            "file_name": "source.mp4",
            "content_type": "video/mp4",
            "size_bytes": 12,
        },
    )
    assert issued.status_code == 200
    return path, issued.json()["upload"]


async def test_cleanup_retries_beyond_media_budget_with_increasing_delays(
    deletion_client: AsyncClient,
    api_app: FastAPI,
    storage: GuardTestStorage,
    test_database: tuple[str, str],
    launcher: RecordingLauncher,
) -> None:
    path, _ = await create_reserved_source(deletion_client)
    await deletion_client.delete(path)
    job = launcher.submissions[-1]
    storage.seal_failures = 5
    delays: list[float] = []
    attempts: list[int] = []

    async def retry(delay: float) -> None:
        delays.append(delay)
        async with await AsyncConnection.connect(test_database[0]) as connection:
            row = await (
                await connection.execute(
                    sql.SQL(
                        "SELECT execution_attempts,error_code,error_message FROM {}.jobs WHERE id=%s"
                    ).format(sql.Identifier(test_database[1])),
                    (job,),
                )
            ).fetchone()
        assert row is not None and row[1] == "CLEANUP_RETRYING" and "secret" not in row[2]
        attempts.append(row[0])
        assert (await deletion_client.get(path)).json()["status"] == "DELETING"
        assert (await deletion_client.delete(path)).status_code == 202

    assert await run_job(job, api_app.state.database, storage, Settings(), sleep=retry)
    assert attempts == [1, 2, 3, 4, 5]
    assert delays == [1, 4, 16, 30, 30]
    assert len(launcher.submissions) == 1
    assert (await deletion_client.get(path)).status_code == 404


@pytest.mark.parametrize("invalid_metadata", [False, True])
async def test_cleanup_runtime_failure_preserves_rows_and_manual_recovery_has_no_budget(
    deletion_client: AsyncClient,
    api_app: FastAPI,
    storage: GuardTestStorage,
    test_database: tuple[str, str],
    launcher: RecordingLauncher,
    invalid_metadata: bool,
) -> None:
    path, _ = await create_reserved_source(deletion_client)
    await deletion_client.delete(path)
    job = launcher.submissions[-1]
    storage.bad_metadata = invalid_metadata
    storage.seal_failures = 0 if invalid_metadata else 10

    async def wait_for_runtime(_: float) -> None:
        await asyncio.sleep(10)

    assert not await run_job(
        job,
        api_app.state.database,
        storage,
        Settings(cleanup_runtime_seconds=0.1),
        sleep=wait_for_runtime,
    )
    assert (await deletion_client.get(path)).json()["status"] == "DELETING"
    async with await AsyncConnection.connect(test_database[0], autocommit=True) as connection:
        row = await (
            await connection.execute(
                sql.SQL("SELECT state,error_code FROM {}.jobs WHERE id=%s").format(
                    sql.Identifier(test_database[1])
                ),
                (job,),
            )
        ).fetchone()
        assert row == ("FAILED", "CLEANUP_RUNTIME_EXHAUSTED")
        await connection.execute(
            sql.SQL("UPDATE {}.jobs SET execution_attempts=8 WHERE id=%s").format(
                sql.Identifier(test_database[1])
            ),
            (job,),
        )
    storage.seal_failures, storage.bad_metadata = 0, False
    assert await JobSubmission(api_app.state.database, launcher).recover(job)
    assert await run_job(job, api_app.state.database, storage, Settings())
    assert (await deletion_client.get(path)).status_code == 404
    assert all(not data for data, _ in storage.objects.values())


@pytest.mark.parametrize("kind", ["VIDEO", "THUMBNAIL"])
async def test_cleanup_guards_real_media_manifest_while_conditional_output_put_is_in_flight(
    deletion_client: AsyncClient,
    api_app: FastAPI,
    storage: GuardTestStorage,
    launcher: RecordingLauncher,
    tmp_path: Path,
    kind: str,
) -> None:
    data = make_source(tmp_path / "source.mp4")
    created = await deletion_client.post("/v1/videos", json={"title": "Race real media"})
    path = created.headers["Location"]
    issued = await deletion_client.post(
        path + ":upload-url",
        json={
            "file_name": "source.mp4",
            "content_type": "video/mp4",
            "size_bytes": len(data),
        },
    )
    upload = issued.json()["upload"]
    await storage.browser_put(upload["url"], data, upload["headers"])
    assert (
        await deletion_client.post(
            path + ":complete-upload", json={"upload_id": upload["upload_id"]}
        )
    ).status_code == 202
    # Source acceptance records independent video and generated-image jobs.
    async with api_app.state.database.connection() as connection:
        row = await (
            await connection.execute(
                "SELECT id FROM jobs WHERE video_id=%s AND kind=%s", (created.json()["id"], kind)
            )
        ).fetchone()
    assert row is not None
    storage.write_started, storage.write_release = Event(), Event()
    processing = create_task(run_job(row[0], api_app.state.database, storage, Settings()))
    await wait_for(storage.write_started.wait(), timeout=10)
    try:
        assert (await deletion_client.delete(path)).status_code == 202
        assert await run_job(launcher.submissions[-1], api_app.state.database, storage, Settings())
    finally:
        storage.write_release.set()
    assert not await wait_for(processing, timeout=10)
    assert (await deletion_client.get(path)).status_code == 404
    assert any(area == "public" for area, _ in storage.objects)
    assert all(not data for data, _ in storage.objects.values())
    assert set(storage.objects) == storage.guards


async def test_cleanup_guards_registered_custom_copy_while_real_image_put_is_in_flight(
    deletion_client: AsyncClient,
    api_app: FastAPI,
    storage: GuardTestStorage,
    launcher: RecordingLauncher,
) -> None:
    created = await deletion_client.post("/v1/videos", json={"title": "Race image"})
    path = created.headers["Location"]
    data = image_bytes()
    issued = await deletion_client.post(
        path + "/thumbnails:upload-url",
        json={
            "file_name": "cover.jpg",
            "content_type": "image/jpeg",
            "size_bytes": len(data),
        },
    )
    upload = issued.json()["upload"]
    await storage.browser_put(upload["url"], data, upload["headers"])
    storage.write_started, storage.write_release = Event(), Event()
    accepting = create_task(
        deletion_client.post(
            path + "/thumbnails:complete-upload", json={"upload_id": upload["upload_id"]}
        )
    )
    await wait_for(storage.write_started.wait(), timeout=5)
    try:
        assert (await deletion_client.delete(path)).status_code == 202
        assert await run_job(launcher.submissions[-1], api_app.state.database, storage, Settings())
    finally:
        storage.write_release.set()
    assert (await wait_for(accepting, timeout=5)).status_code == 409
    assert (await deletion_client.get(path)).status_code == 404
    assert len(storage.guards) == 2
    assert all(not data for data, _ in storage.objects.values())


async def test_recovered_cleanup_token_fences_old_execution_before_row_removal(
    deletion_client: AsyncClient,
    api_app: FastAPI,
    storage: GuardTestStorage,
    launcher: RecordingLauncher,
) -> None:
    path, _ = await create_reserved_source(deletion_client)
    await deletion_client.delete(path)
    job = launcher.submissions[-1]
    storage.head_started, storage.head_release = Event(), Event()
    interrupted = create_task(run_job(job, api_app.state.database, storage, Settings()))
    await wait_for(storage.head_started.wait(), timeout=3)
    try:
        with pytest.raises(VideoConflict, match="terminated"):
            await JobSubmission(api_app.state.database, launcher).recover(job)
        assert await JobSubmission(api_app.state.database, launcher).recover(
            job, previous_execution_terminated=True
        )
    finally:
        storage.head_release.set()
    assert not await wait_for(interrupted, timeout=3)
    assert (await deletion_client.get(path)).json()["status"] == "DELETING"
    assert await run_job(job, api_app.state.database, storage, Settings())
    assert (await deletion_client.get(path)).status_code == 404
