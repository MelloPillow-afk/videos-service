"""Deletion acceptance fences real application state before physical cleanup."""

import asyncio
import json
import os
import sys
from asyncio import Event, create_subprocess_exec, create_task, gather, wait_for
from collections.abc import AsyncIterator
from uuid import UUID

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from psycopg import AsyncConnection, sql

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
    assert rows[0][2] and rows[0][3] == "CLEANUP_POLICY_REQUIRED"
    assert launcher.submissions == [UUID(rows[0][0].hex)]


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
