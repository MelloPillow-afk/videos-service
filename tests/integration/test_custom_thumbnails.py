"""Custom thumbnails use real images, HTTP, PostgreSQL, and controlled storage."""

from asyncio import Event, create_task, gather, wait_for
from collections.abc import AsyncIterator
from datetime import datetime, timedelta
from io import BytesIO
from urllib.parse import unquote, urlsplit

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from PIL import Image
from psycopg import AsyncConnection, sql

from src.app import create_app
from src.providers.storage import StorageArea, StorageConflictError, TemporaryStorageError
from tests.providers import LocalSigningKeys
from tests.storage_provider import MemoryStorage

pytestmark = pytest.mark.integration


def image_bytes(format: str = "JPEG", size: tuple[int, int] = (1280, 720)) -> bytes:
    output = BytesIO()
    Image.new("RGB", size, color=(70, 110, 150)).save(output, format=format)
    return output.getvalue()


class ThumbnailStorage(MemoryStorage):
    def __init__(self) -> None:
        super().__init__()
        self.write_started: Event | None = None
        self.write_release: Event | None = None
        self.fail_after_write = False

    async def write(
        self,
        area: StorageArea,
        key: str,
        data: bytes,
        content_type: str,
        *,
        create_only: bool = True,
    ) -> None:
        assert create_only
        if area == "public" and self.write_started is not None and self.write_release is not None:
            self.write_started.set()
            await self.write_release.wait()
        await super().write(area, key, data, content_type, create_only=create_only)
        if area == "public" and self.fail_after_write:
            self.fail_after_write = False
            raise TemporaryStorageError("private diagnostic must not escape")


@pytest.fixture
def thumbnail_storage() -> ThumbnailStorage:
    return ThumbnailStorage()


@pytest_asyncio.fixture
async def thumbnail_client(
    api_app: FastAPI, signing_keys: LocalSigningKeys, thumbnail_storage: MemoryStorage
) -> AsyncIterator[AsyncClient]:
    app = create_app(api_app.state.settings, signing_keys=signing_keys, storage=thumbnail_storage)
    async with (
        app.router.lifespan_context(app),
        AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client,
    ):
        yield client


async def create_draft(client: AsyncClient, keys: LocalSigningKeys) -> str:
    response = await client.post(
        "/v1/videos",
        headers={"Authorization": "Bearer " + keys.token()},
        json={"title": "Thumbnail lesson"},
    )
    assert response.status_code == 201
    return response.headers["Location"]


@pytest.mark.parametrize(
    "format,content_type", [("JPEG", "image/jpeg"), ("PNG", "image/png"), ("WEBP", "image/webp")]
)
async def test_valid_custom_image_becomes_active_before_video_processing(
    thumbnail_client: AsyncClient,
    thumbnail_storage: MemoryStorage,
    signing_keys: LocalSigningKeys,
    format: str,
    content_type: str,
) -> None:
    path = await create_draft(thumbnail_client, signing_keys)
    headers = {"Authorization": "Bearer " + signing_keys.token()}
    data = image_bytes(format)
    issued = await thumbnail_client.post(
        path + "/thumbnails:upload-url",
        headers=headers,
        json={"file_name": "cover", "content_type": content_type, "size_bytes": len(data)},
    )
    assert issued.status_code == 200
    upload = issued.json()["upload"]
    assert upload["headers"] == {"Content-Type": content_type, "If-None-Match": "*"}
    await thumbnail_storage.browser_put(upload["url"], data, upload["headers"])
    complete = await thumbnail_client.post(
        path + "/thumbnails:complete-upload",
        headers=headers,
        json={"upload_id": upload["upload_id"]},
    )
    assert complete.status_code == 200
    thumbnail = complete.json()["thumbnail"]
    assert thumbnail["status"] == "READY" and thumbnail["source"] == "CUSTOM"
    assert thumbnail["url"].startswith("https://media.example.com/")
    public_key = thumbnail["url"].removeprefix("https://media.example.com/")
    assert await thumbnail_storage.read("public", public_key, 5242880) == data
    repeat = await thumbnail_client.post(
        path + "/thumbnails:complete-upload",
        headers=headers,
        json={"upload_id": upload["upload_id"]},
    )
    assert repeat.json() == complete.json()
    detail = await thumbnail_client.get(path, headers=headers)
    assert detail.json()["status"] == "CREATED"
    assert detail.json()["thumbnail"] == thumbnail


async def authorize_image(
    client: AsyncClient,
    path: str,
    headers: dict[str, str],
    data: bytes,
    content_type: str = "image/jpeg",
    declared: int | None = None,
) -> dict[str, object]:
    response = await client.post(
        path + "/thumbnails:upload-url",
        headers=headers,
        json={
            "file_name": "cover",
            "content_type": content_type,
            "size_bytes": declared if declared is not None else len(data),
        },
    )
    assert response.status_code == 200
    return response.json()["upload"]


@pytest.mark.parametrize(
    "failure",
    [
        "spoof",
        "corrupt",
        "truncated",
        "dimensions",
        "metadata",
        "size",
        "oversized",
        "bounded-read",
        "missing",
    ],
)
async def test_invalid_image_preserves_the_existing_custom_selection(
    thumbnail_client: AsyncClient,
    thumbnail_storage: MemoryStorage,
    signing_keys: LocalSigningKeys,
    failure: str,
) -> None:
    path = await create_draft(thumbnail_client, signing_keys)
    headers = {"Authorization": "Bearer " + signing_keys.token()}
    original = image_bytes()
    first = await authorize_image(thumbnail_client, path, headers, original)
    await thumbnail_storage.browser_put(
        str(first["url"]), original, {"Content-Type": "image/jpeg", "If-None-Match": "*"}
    )
    active = await thumbnail_client.post(
        path + "/thumbnails:complete-upload",
        headers=headers,
        json={"upload_id": first["upload_id"]},
    )
    assert active.status_code == 200
    data = {
        "spoof": image_bytes("PNG"),
        "corrupt": b"not an image",
        "truncated": original[:500],
        "dimensions": image_bytes(size=(720, 1280)),
        "metadata": original,
        "size": original,
        "oversized": original + b"x" * 5242880,
        "bounded-read": original + b"x" * 5242880,
        "missing": original,
    }[failure]
    declared = len(original) if failure in ("size", "oversized", "bounded-read") else len(data)
    if failure == "size":
        declared += 1
    attempt = await authorize_image(thumbnail_client, path, headers, data, declared=declared)
    key = unquote(urlsplit(str(attempt["url"])).path.lstrip("/"))
    if failure != "missing":
        await thumbnail_storage.write(
            "private", key, data, "image/png" if failure == "metadata" else "image/jpeg"
        )
    if failure == "bounded-read":
        thumbnail_storage.size_overrides[key] = declared
    rejected = await thumbnail_client.post(
        path + "/thumbnails:complete-upload",
        headers=headers,
        json={"upload_id": attempt["upload_id"]},
    )
    assert rejected.status_code == (
        413 if failure in ("oversized", "bounded-read") else 404 if failure == "missing" else 400
    )
    detail = await thumbnail_client.get(path, headers=headers)
    assert detail.json()["thumbnail"] == active.json()["thumbnail"]
    assert len(await thumbnail_storage.list("public", "videos/")) == 1


async def test_exact_five_mib_image_and_fifteen_minute_authorization(
    thumbnail_client: AsyncClient,
    thumbnail_storage: MemoryStorage,
    signing_keys: LocalSigningKeys,
    test_database: tuple[str, str],
) -> None:
    path = await create_draft(thumbnail_client, signing_keys)
    headers = {"Authorization": "Bearer " + signing_keys.token()}
    original = image_bytes()
    data = original + b"\0" * (5242880 - len(original))
    attempt = await authorize_image(thumbnail_client, path, headers, data)
    url, schema = test_database
    async with await AsyncConnection.connect(url, autocommit=True) as connection:
        row = await (
            await connection.execute(
                sql.SQL("SELECT created_at,expires_at FROM {}.upload_attempts WHERE id=%s").format(
                    sql.Identifier(schema)
                ),
                (attempt["upload_id"],),
            )
        ).fetchone()
    assert row is not None and row[1] - row[0] == timedelta(minutes=15)
    assert datetime.fromisoformat(str(attempt["expires_at"])) == row[1]
    await thumbnail_storage.browser_put(
        str(attempt["url"]), data, {"Content-Type": "image/jpeg", "If-None-Match": "*"}
    )
    accepted = await thumbnail_client.post(
        path + "/thumbnails:complete-upload",
        headers=headers,
        json={"upload_id": attempt["upload_id"]},
    )
    assert accepted.status_code == 200
    before = await thumbnail_storage.list("private", "videos/")
    rejected = await thumbnail_client.post(
        path + "/thumbnails:upload-url",
        headers=headers,
        json={"file_name": "large.jpg", "content_type": "image/jpeg", "size_bytes": 5242881},
    )
    assert rejected.status_code == 413
    assert await thumbnail_storage.list("private", "videos/") == before


@pytest.mark.parametrize(
    "generated,expected",
    [
        (
            "READY",
            {
                "status": "READY",
                "source": "GENERATED",
                "url": "https://media.example.com/generated.jpg",
            },
        ),
        ("PENDING", {"status": "PENDING", "source": "NONE", "url": None}),
        ("FAILED", {"status": "FAILED", "source": "NONE", "url": None}),
    ],
)
async def test_removal_is_idempotent_restores_fallback_and_invalidates_attempts(
    thumbnail_client: AsyncClient,
    thumbnail_storage: MemoryStorage,
    signing_keys: LocalSigningKeys,
    test_database: tuple[str, str],
    generated: str,
    expected: dict[str, str | None],
) -> None:
    path = await create_draft(thumbnail_client, signing_keys)
    headers = {"Authorization": "Bearer " + signing_keys.token()}
    data = image_bytes()
    first = await authorize_image(thumbnail_client, path, headers, data)
    await thumbnail_storage.browser_put(
        str(first["url"]), data, {"Content-Type": "image/jpeg", "If-None-Match": "*"}
    )
    assert (
        await thumbnail_client.post(
            path + "/thumbnails:complete-upload",
            headers=headers,
            json={"upload_id": first["upload_id"]},
        )
    ).status_code == 200
    second = await authorize_image(thumbnail_client, path, headers, data)
    await thumbnail_storage.browser_put(
        str(second["url"]), data, {"Content-Type": "image/jpeg", "If-None-Match": "*"}
    )
    url, schema = test_database
    async with await AsyncConnection.connect(url, autocommit=True) as connection:
        await connection.execute(
            sql.SQL(
                "UPDATE {}.videos SET generated_thumbnail_status=%s,generated_thumbnail_key=%s WHERE id=%s"
            ).format(sql.Identifier(schema)),
            (generated, "generated.jpg" if generated == "READY" else None, path.rsplit("/", 1)[1]),
        )
    for _ in range(2):
        removed = await thumbnail_client.delete(path + "/thumbnails", headers=headers)
        assert removed.status_code == 200 and removed.json()["thumbnail"] == expected
    for upload in [first, second]:
        stale = await thumbnail_client.post(
            path + "/thumbnails:complete-upload",
            headers=headers,
            json={"upload_id": upload["upload_id"]},
        )
        assert stale.status_code == 409
    assert (await thumbnail_client.get(path, headers=headers)).json()["thumbnail"] == expected


async def test_duplicate_concurrent_confirmation_keeps_one_image_and_acceptance_timestamp(
    thumbnail_client: AsyncClient,
    thumbnail_storage: ThumbnailStorage,
    signing_keys: LocalSigningKeys,
    test_database: tuple[str, str],
) -> None:
    path = await create_draft(thumbnail_client, signing_keys)
    headers = {"Authorization": "Bearer " + signing_keys.token()}
    data = image_bytes()
    attempt = await authorize_image(thumbnail_client, path, headers, data)
    await thumbnail_storage.browser_put(
        str(attempt["url"]), data, {"Content-Type": "image/jpeg", "If-None-Match": "*"}
    )
    with pytest.raises(StorageConflictError):
        await thumbnail_storage.browser_put(
            str(attempt["url"]), b"different", {"Content-Type": "image/jpeg", "If-None-Match": "*"}
        )
    responses = await gather(
        *(
            thumbnail_client.post(
                path + "/thumbnails:complete-upload",
                headers=headers,
                json={"upload_id": attempt["upload_id"]},
            )
            for _ in range(2)
        )
    )
    assert all(response.status_code == 200 for response in responses)
    assert responses[0].json() == responses[1].json()
    assert len(await thumbnail_storage.list("public", "videos/")) == 1
    url, schema = test_database
    async with await AsyncConnection.connect(url, autocommit=True) as connection:
        first = await (
            await connection.execute(
                sql.SQL(
                    "SELECT state,accepted_at,public_object_key FROM {}.upload_attempts WHERE id=%s"
                ).format(sql.Identifier(schema)),
                (attempt["upload_id"],),
            )
        ).fetchone()
        assert first is not None and first[0] == "ACCEPTED" and first[1] and first[2]
        await thumbnail_client.post(
            path + "/thumbnails:complete-upload",
            headers=headers,
            json={"upload_id": attempt["upload_id"]},
        )
        duplicate = await (
            await connection.execute(
                sql.SQL(
                    "SELECT state,accepted_at,public_object_key FROM {}.upload_attempts WHERE id=%s"
                ).format(sql.Identifier(schema)),
                (attempt["upload_id"],),
            )
        ).fetchone()
    assert duplicate == first


@pytest.mark.parametrize("interruption", ["remove", "supersede", "delete"])
async def test_inflight_public_copy_cannot_reactivate_removed_superseded_or_deleting_image(
    thumbnail_client: AsyncClient,
    thumbnail_storage: ThumbnailStorage,
    signing_keys: LocalSigningKeys,
    test_database: tuple[str, str],
    interruption: str,
) -> None:
    path = await create_draft(thumbnail_client, signing_keys)
    headers = {"Authorization": "Bearer " + signing_keys.token()}
    data = image_bytes()
    attempt = await authorize_image(thumbnail_client, path, headers, data)
    await thumbnail_storage.browser_put(
        str(attempt["url"]), data, {"Content-Type": "image/jpeg", "If-None-Match": "*"}
    )
    thumbnail_storage.write_started, thumbnail_storage.write_release = Event(), Event()
    completing = create_task(
        thumbnail_client.post(
            path + "/thumbnails:complete-upload",
            headers=headers,
            json={"upload_id": attempt["upload_id"]},
        )
    )
    await wait_for(thumbnail_storage.write_started.wait(), timeout=3)
    url, schema = test_database
    try:
        async with await AsyncConnection.connect(url, autocommit=True) as connection:
            row = await (
                await connection.execute(
                    sql.SQL(
                        "SELECT public_object_key,state FROM {}.upload_attempts WHERE id=%s"
                    ).format(sql.Identifier(schema)),
                    (attempt["upload_id"],),
                )
            ).fetchone()
            assert row is not None and row[0] and row[1] == "PENDING"
            registered_key = str(row[0])
            if interruption == "delete":
                await connection.execute(
                    sql.SQL("UPDATE {}.videos SET status='DELETING' WHERE id=%s").format(
                        sql.Identifier(schema)
                    ),
                    (path.rsplit("/", 1)[1],),
                )
        if interruption == "remove":
            assert (
                await thumbnail_client.delete(path + "/thumbnails", headers=headers)
            ).status_code == 200
        if interruption == "supersede":
            await authorize_image(thumbnail_client, path, headers, data)
    finally:
        thumbnail_storage.write_release.set()
    rejected = await wait_for(completing, timeout=3)
    assert rejected.status_code == 409
    detail = await thumbnail_client.get(path, headers=headers)
    assert detail.json()["thumbnail"] == {"status": "PENDING", "source": "NONE", "url": None}
    # Orphaned output remains registered for explicit video cleanup. This does
    # not claim that database fencing itself stops a provider write in flight.
    assert await thumbnail_storage.read("public", registered_key, 5242880) == data


async def test_unknown_public_write_outcome_is_safe_to_retry(
    thumbnail_client: AsyncClient,
    thumbnail_storage: ThumbnailStorage,
    signing_keys: LocalSigningKeys,
) -> None:
    path = await create_draft(thumbnail_client, signing_keys)
    headers = {"Authorization": "Bearer " + signing_keys.token()}
    data = image_bytes()
    attempt = await authorize_image(thumbnail_client, path, headers, data)
    await thumbnail_storage.browser_put(
        str(attempt["url"]), data, {"Content-Type": "image/jpeg", "If-None-Match": "*"}
    )
    thumbnail_storage.fail_after_write = True
    failed = await thumbnail_client.post(
        path + "/thumbnails:complete-upload",
        headers=headers,
        json={"upload_id": attempt["upload_id"]},
    )
    assert failed.status_code == 503 and "private diagnostic" not in failed.text
    assert (await thumbnail_client.get(path, headers=headers)).json()["thumbnail"][
        "source"
    ] == "NONE"
    recovered = await thumbnail_client.post(
        path + "/thumbnails:complete-upload",
        headers=headers,
        json={"upload_id": attempt["upload_id"]},
    )
    assert recovered.status_code == 200 and recovered.json()["thumbnail"]["source"] == "CUSTOM"


async def test_current_role_is_required_for_all_thumbnail_mutations(
    thumbnail_client: AsyncClient,
    signing_keys: LocalSigningKeys,
    test_database: tuple[str, str],
) -> None:
    path = await create_draft(thumbnail_client, signing_keys)
    token_headers = {"Authorization": "Bearer " + signing_keys.token()}
    requests = [
        (
            "POST",
            path + "/thumbnails:upload-url",
            {"file_name": "cover", "content_type": "image/jpeg", "size_bytes": 100},
        ),
        (
            "POST",
            path + "/thumbnails:complete-upload",
            {"upload_id": "550e8400-e29b-41d4-a716-446655440000"},
        ),
        ("DELETE", path + "/thumbnails", None),
    ]
    for method, endpoint, body in requests:
        response = await thumbnail_client.request(method, endpoint, json=body)
        assert response.status_code == 401
    url, schema = test_database
    async with await AsyncConnection.connect(url, autocommit=True) as connection:
        await connection.execute(
            sql.SQL("UPDATE {}.\"user\" SET role='user'").format(sql.Identifier(schema + "_auth"))
        )
    for method, endpoint, body in requests:
        response = await thumbnail_client.request(
            method, endpoint, headers=token_headers, json=body
        )
        assert response.status_code == 403


async def test_stale_cross_video_and_deleting_thumbnail_mutations_are_rejected(
    thumbnail_client: AsyncClient,
    thumbnail_storage: MemoryStorage,
    signing_keys: LocalSigningKeys,
    test_database: tuple[str, str],
) -> None:
    path = await create_draft(thumbnail_client, signing_keys)
    other = await create_draft(thumbnail_client, signing_keys)
    headers = {"Authorization": "Bearer " + signing_keys.token()}
    data = image_bytes()
    first = await authorize_image(thumbnail_client, path, headers, data)
    await thumbnail_storage.browser_put(
        str(first["url"]), data, {"Content-Type": "image/jpeg", "If-None-Match": "*"}
    )
    second = await authorize_image(thumbnail_client, path, headers, data)
    assert first["url"] != second["url"] and first["upload_id"] != second["upload_id"]
    for endpoint in [path, other]:
        assert (
            await thumbnail_client.post(
                endpoint + "/thumbnails:complete-upload",
                headers=headers,
                json={"upload_id": first["upload_id"]},
            )
        ).status_code == 409
    assert await thumbnail_storage.list("public", "videos/") == []
    unsupported = await thumbnail_client.post(
        path + "/thumbnails:upload-url",
        headers=headers,
        json={"file_name": "cover.gif", "content_type": "image/gif", "size_bytes": 100},
    )
    assert unsupported.status_code == 400
    url, schema = test_database
    async with await AsyncConnection.connect(url, autocommit=True) as connection:
        await connection.execute(
            sql.SQL("UPDATE {}.videos SET status='DELETING' WHERE id=%s").format(
                sql.Identifier(schema)
            ),
            (path.rsplit("/", 1)[1],),
        )
    assert (
        await thumbnail_client.post(
            path + "/thumbnails:upload-url",
            headers=headers,
            json={"file_name": "cover.jpg", "content_type": "image/jpeg", "size_bytes": 100},
        )
    ).status_code == 409
    assert (
        await thumbnail_client.post(
            path + "/thumbnails:complete-upload",
            headers=headers,
            json={"upload_id": second["upload_id"]},
        )
    ).status_code == 409
    assert (await thumbnail_client.delete(path + "/thumbnails", headers=headers)).status_code == 409
    absent = "/v1/videos/550e8400-e29b-41d4-a716-446655440001"
    assert (
        await thumbnail_client.delete(absent + "/thumbnails", headers=headers)
    ).status_code == 404
