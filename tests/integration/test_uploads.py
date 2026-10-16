"""Source upload acceptance through real HTTP and PostgreSQL."""

import asyncio
import json
from collections.abc import AsyncIterator
from datetime import datetime, timedelta
from typing import cast
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest
import pytest_asyncio
from botocore.stub import Stubber
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from psycopg import AsyncConnection, sql
from pydantic import SecretStr

from src.app import create_app
from src.providers.cloud_run import CloudRunJobLauncher
from src.providers.r2 import R2Storage
from src.providers.storage import StorageConflictError
from tests.job_provider import RecordingLauncher
from tests.providers import LocalSigningKeys
from tests.storage_provider import MemoryStorage

pytestmark = pytest.mark.integration


@pytest_asyncio.fixture
async def upload_client(
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


async def test_source_instructions_persist_uploading_state(upload_client: AsyncClient) -> None:
    draft = await upload_client.post("/v1/videos", json={"title": "Source upload"})
    path = draft.headers["Location"]
    response = await upload_client.post(
        path + ":upload-url",
        json={"file_name": "source.mp4", "content_type": "video/mp4", "size_bytes": 12},
    )
    assert response.status_code == 200
    assert response.json()["video_id"] == draft.json()["id"]
    assert response.json()["upload"]["headers"]["If-None-Match"] == "*"
    assert (await upload_client.get(path)).json()["status"] == "UPLOADING"
    assert datetime.fromisoformat(response.json()["upload"]["expires_at"]) - datetime.fromisoformat(
        (await upload_client.get(path)).json()["updated_at"]
    ) == timedelta(minutes=15)


async def prepare_upload(client: AsyncClient, *, size: int = 12) -> tuple[str, dict[str, object]]:
    draft = await client.post("/v1/videos", json={"title": "Source upload"})
    path = draft.headers["Location"]
    response = await client.post(
        path + ":upload-url",
        json={"file_name": "source.mp4", "content_type": "video/mp4", "size_bytes": size},
    )
    assert response.status_code == 200
    return path, response.json()["upload"]


async def test_confirmation_persists_independent_jobs_and_is_idempotent(
    upload_client: AsyncClient, storage: MemoryStorage, launcher: RecordingLauncher
) -> None:
    path, upload = await prepare_upload(upload_client)
    await storage.browser_put(
        str(upload["url"]), b"video-source", cast(dict[str, str], upload["headers"])
    )
    response = await upload_client.post(
        path + ":complete-upload", json={"upload_id": upload["upload_id"]}
    )
    assert response.status_code == 202
    assert response.json()["status"] == "QUEUED"
    assert response.json()["thumbnail_status"] == "PENDING"
    assert (await upload_client.get(path)).json()["size_bytes"] == 12
    assert (await upload_client.get(path)).json()["status"] == "QUEUED"
    assert len(launcher.submissions) == 2
    repeated = await upload_client.post(
        path + ":complete-upload", json={"upload_id": upload["upload_id"]}
    )
    assert repeated.json() == response.json()
    assert len(launcher.submissions) == 2
    with pytest.raises(StorageConflictError):
        await storage.browser_put(
            str(upload["url"]), b"overwritten!", cast(dict[str, str], upload["headers"])
        )
    assert "signature" not in (await upload_client.get(path)).text
    assert "upload_id" not in (await upload_client.get(path)).text


async def test_renewed_attempt_isolated_from_old_upload_url(
    upload_client: AsyncClient, storage: MemoryStorage, launcher: RecordingLauncher
) -> None:
    path, first = await prepare_upload(upload_client)
    response = await upload_client.post(
        path + ":upload-url",
        json={"file_name": "renewed.mp4", "content_type": "video/mp4", "size_bytes": 12},
    )
    second = response.json()["upload"]
    assert first["upload_id"] != second["upload_id"] and first["url"] != second["url"]
    await storage.browser_put(
        str(first["url"]), b"video-source", cast(dict[str, str], first["headers"])
    )
    assert (
        await upload_client.post(path + ":complete-upload", json={"upload_id": first["upload_id"]})
    ).status_code == 409
    assert (await upload_client.get(path)).json()["status"] == "UPLOADING"
    assert launcher.submissions == []
    await storage.browser_put(second["url"], b"video-source", second["headers"])
    assert (
        await upload_client.post(path + ":complete-upload", json={"upload_id": second["upload_id"]})
    ).status_code == 202


@pytest.mark.parametrize(
    "problem,status", [("missing", 404), ("size", 400), ("oversized", 413), ("type", 400)]
)
async def test_rejected_confirmation_preserves_uploading_and_records_no_work(
    upload_client: AsyncClient,
    storage: MemoryStorage,
    launcher: RecordingLauncher,
    problem: str,
    status: int,
) -> None:
    path, upload = await prepare_upload(upload_client)
    if problem != "missing":
        await storage.browser_put(
            str(upload["url"]),
            b"bad" if problem == "size" else b"video-source",
            cast(dict[str, str], upload["headers"]),
        )
        key = urlsplit(str(upload["url"])).path.lstrip("/")
        if problem == "oversized":
            storage.size_overrides[key] = 104857601
        if problem == "type":
            storage.objects[("private", key)] = b"video-source", "application/octet-stream"
    response = await upload_client.post(
        path + ":complete-upload", json={"upload_id": upload["upload_id"]}
    )
    assert response.status_code == status
    assert (await upload_client.get(path)).json()["status"] == "UPLOADING"
    assert launcher.submissions == []
    # Admission is not a transfer ceiling: the rejected object remains for explicit cleanup.
    assert len(storage.objects) == (0 if problem == "missing" else 1)


async def test_excessive_declared_size_is_rejected_before_authorization(
    upload_client: AsyncClient, storage: MemoryStorage
) -> None:
    draft = await upload_client.post("/v1/videos", json={"title": "Admission"})
    response = await upload_client.post(
        draft.headers["Location"] + ":upload-url",
        json={"file_name": "large.mp4", "content_type": "video/mp4", "size_bytes": 104857601},
    )
    assert response.status_code == 413
    assert (await upload_client.get(draft.headers["Location"])).json()["status"] == "CREATED"
    assert storage.objects == {}


async def test_concurrent_confirmation_submits_each_independent_job_once(
    upload_client: AsyncClient, storage: MemoryStorage, launcher: RecordingLauncher
) -> None:
    path, upload = await prepare_upload(upload_client)
    await storage.browser_put(
        str(upload["url"]), b"video-source", cast(dict[str, str], upload["headers"])
    )
    responses = await asyncio.gather(
        *(
            upload_client.post(path + ":complete-upload", json={"upload_id": upload["upload_id"]})
            for _ in range(8)
        )
    )
    assert all(response.status_code == 202 for response in responses)
    assert len({response.json()["processing_job_id"] for response in responses}) == 1
    assert len(launcher.submissions) == 2


async def test_deletion_during_object_verification_blocks_acceptance(
    upload_client: AsyncClient,
    storage: MemoryStorage,
    launcher: RecordingLauncher,
    test_database: tuple[str, str],
) -> None:
    path, upload = await prepare_upload(upload_client)
    await storage.browser_put(
        str(upload["url"]), b"video-source", cast(dict[str, str], upload["headers"])
    )
    storage.head_started, storage.head_release = asyncio.Event(), asyncio.Event()
    request = asyncio.create_task(
        upload_client.post(path + ":complete-upload", json={"upload_id": upload["upload_id"]})
    )
    await asyncio.wait_for(storage.head_started.wait(), 2)
    url, schema = test_database
    async with await AsyncConnection.connect(url, autocommit=True) as connection:
        await connection.execute(
            sql.SQL("UPDATE {}.videos SET status='DELETING'").format(sql.Identifier(schema))
        )
    storage.head_release.set()
    assert (await request).status_code == 409
    assert launcher.submissions == []
    assert (await upload_client.get(path)).json()["status"] == "DELETING"


async def test_failed_launch_is_durable_accepted_work_and_not_implicit_retry(
    upload_client: AsyncClient,
    storage: MemoryStorage,
    launcher: RecordingLauncher,
    test_database: tuple[str, str],
) -> None:
    path, upload = await prepare_upload(upload_client)
    await storage.browser_put(
        str(upload["url"]), b"video-source", cast(dict[str, str], upload["headers"])
    )
    launcher.fail = True
    response = await upload_client.post(
        path + ":complete-upload", json={"upload_id": upload["upload_id"]}
    )
    assert response.status_code == 202
    url, schema = test_database
    # The approved persistence acceptance seam includes durable operator-visible launch records.
    async with await AsyncConnection.connect(url, autocommit=True) as connection:
        cursor = await connection.execute(
            sql.SQL(
                "SELECT kind,state,error_code,execution_attempts FROM {}.jobs ORDER BY kind"
            ).format(sql.Identifier(schema))
        )
        assert await cursor.fetchall() == [
            ("THUMBNAIL", "LAUNCH_FAILED", "LAUNCH_UNCONFIRMED", 0),
            ("VIDEO", "LAUNCH_FAILED", "LAUNCH_UNCONFIRMED", 0),
        ]
    assert (
        await upload_client.post(path + ":complete-upload", json={"upload_id": upload["upload_id"]})
    ).json() == response.json()
    assert len(launcher.submissions) == 2


async def test_r2_signed_instructions_bind_create_once_header(
    api_app: FastAPI, signing_keys: LocalSigningKeys
) -> None:
    settings = api_app.state.settings.model_copy(
        update={
            "r2_endpoint_url": "https://account.r2.cloudflarestorage.com",
            "r2_private_bucket": "private",
            "r2_public_bucket": "public",
            "r2_access_key_id": SecretStr("local-test-key"),
            "r2_secret_access_key": SecretStr("local-test-secret"),
        }
    )
    storage = R2Storage(settings)
    app = create_app(
        settings, signing_keys=signing_keys, storage=storage, launcher=RecordingLauncher()
    )
    async with (
        app.router.lifespan_context(app),
        AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            headers={"Authorization": "Bearer " + signing_keys.token()},
        ) as client,
    ):
        path, upload = await prepare_upload(client)
        query = parse_qs(urlsplit(str(upload["url"])).query)
        assert query["X-Amz-Expires"] == ["900"]
        assert set(query["X-Amz-SignedHeaders"][0].split(";")) == {
            "content-type",
            "host",
            "if-none-match",
        }
        assert upload["headers"] == {"Content-Type": "video/mp4", "If-None-Match": "*"}
        key = urlsplit(str(upload["url"])).path.removeprefix("/private/")
        with Stubber(storage.client) as provider:
            provider.add_response(
                "head_object",
                {"ContentLength": 12, "ContentType": "video/mp4"},
                {"Bucket": "private", "Key": key},
            )
            response = await client.post(
                path + ":complete-upload", json={"upload_id": upload["upload_id"]}
            )
            assert response.status_code == 202
            provider.assert_no_pending_responses()


async def test_cloud_run_adapter_submits_job_ids_without_waiting_for_media(
    api_app: FastAPI, signing_keys: LocalSigningKeys, storage: MemoryStorage
) -> None:
    requests: list[httpx.Request] = []

    async def provider(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.host == "metadata.google.internal":
            assert request.headers["Metadata-Flavor"] == "Google"
            return httpx.Response(200, json={"access_token": "controlled-runtime-token"})
        assert request.headers["Authorization"] == "Bearer controlled-runtime-token"
        assert (
            str(request.url)
            == "https://run.googleapis.com/v2/projects/showcase/locations/us-central1/jobs/media:run"
        )
        args = json.loads(request.content)["overrides"]["containerOverrides"][0]["args"]
        assert args[:2] == ["run", "--job-id"]
        return httpx.Response(
            200, json={"name": "projects/showcase/locations/us-central1/operations/" + args[2]}
        )

    settings = api_app.state.settings.model_copy(
        update={"cloud_run_job_resource": "projects/showcase/locations/us-central1/jobs/media"}
    )
    app = create_app(
        settings,
        signing_keys=signing_keys,
        storage=storage,
        launcher=CloudRunJobLauncher(settings, transport=httpx.MockTransport(provider)),
    )
    async with (
        app.router.lifespan_context(app),
        AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            headers={"Authorization": "Bearer " + signing_keys.token()},
        ) as client,
    ):
        path, upload = await prepare_upload(client)
        await storage.browser_put(
            str(upload["url"]), b"video-source", cast(dict[str, str], upload["headers"])
        )
        response = await client.post(
            path + ":complete-upload", json={"upload_id": upload["upload_id"]}
        )
        assert response.status_code == 202
        submissions = [request for request in requests if request.method == "POST"]
        assert len(submissions) == 2
        assert response.json()["processing_job_id"] in {
            json.loads(request.content)["overrides"]["containerOverrides"][0]["args"][2]
            for request in submissions
        }
        assert (await client.get(path)).json()["status"] == "QUEUED"


async def test_confirmed_source_cannot_be_renewed_or_reaccepted_after_deletion(
    upload_client: AsyncClient, storage: MemoryStorage, test_database: tuple[str, str]
) -> None:
    path, upload = await prepare_upload(upload_client)
    await storage.browser_put(
        str(upload["url"]), b"video-source", cast(dict[str, str], upload["headers"])
    )
    assert (
        await upload_client.post(path + ":complete-upload", json={"upload_id": upload["upload_id"]})
    ).status_code == 202
    assert (
        await upload_client.post(
            path + ":upload-url",
            json={"file_name": "replace.mp4", "content_type": "video/mp4", "size_bytes": 12},
        )
    ).status_code == 409
    url, schema = test_database
    async with await AsyncConnection.connect(url, autocommit=True) as connection:
        await connection.execute(
            sql.SQL("UPDATE {}.videos SET status='DELETING'").format(sql.Identifier(schema))
        )
    assert (
        await upload_client.post(path + ":complete-upload", json={"upload_id": upload["upload_id"]})
    ).status_code == 409
