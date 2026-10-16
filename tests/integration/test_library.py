"""Published-library behavior through HTTP and PostgreSQL."""

from asyncio import gather
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from psycopg import AsyncConnection, sql

from tests.providers import LocalSigningKeys

pytestmark = pytest.mark.integration


@pytest_asyncio.fixture
async def library_client(api_app: FastAPI) -> AsyncIterator[AsyncClient]:
    async with (
        api_app.router.lifespan_context(api_app),
        AsyncClient(transport=ASGITransport(app=api_app), base_url="http://test") as client,
    ):
        yield client


async def seed_video(
    test_database: tuple[str, str],
    *,
    title: str = "A lesson",
    status: str = "READY",
    published: bool = False,
    id: UUID | None = None,
    created_at: datetime | None = None,
    generated_status: str = "PENDING",
    generated_key: str | None = None,
    custom_key: str | None = None,
    error: bool = False,
) -> str:
    url, schema = test_database
    identity = id or uuid4()
    now = created_at or datetime(2026, 10, 16, tzinfo=UTC)
    async with await AsyncConnection.connect(url, autocommit=True) as connection:
        await connection.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(schema)))
        await connection.execute(
            """INSERT INTO videos
            (id,title,status,publication_status,published_at,created_at,updated_at,
             source_key,playback_key,generated_thumbnail_status,generated_thumbnail_key,
             custom_thumbnail_key,processing_error_code,processing_error_message)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (
                identity,
                title,
                status,
                "PUBLISHED" if published else "DRAFT",
                now if published else None,
                now,
                now,
                "private/original.mp4",
                f"videos/{identity}/hls/master.m3u8" if status == "READY" else None,
                generated_status,
                generated_key,
                custom_key,
                "TRANSCODE_FAILED" if error else None,
                "Video processing failed." if error else None,
            ),
        )
    return str(identity)


async def test_anonymous_library_contains_only_ready_published_videos(
    library_client: AsyncClient, test_database: tuple[str, str]
) -> None:
    visible = await seed_video(test_database, published=True)
    hidden = [
        await seed_video(test_database),
        await seed_video(test_database, status="PROCESSING"),
        await seed_video(test_database, status="DELETING", published=True),
    ]
    assert (await library_client.get(f"/v1/videos/{visible}")).status_code == 200
    for id in hidden:
        assert (await library_client.get(f"/v1/videos/{id}")).status_code == 404
    response = await library_client.get("/v1/videos")
    assert response.status_code == 200
    assert [v["id"] for v in response.json()["data"]] == [visible]
    assert response.json()["pagination"] == {"has_more": False, "next_page_token": None}
    assert "private/" not in response.text


async def test_search_pages_have_stable_tie_order_and_filter_bound_cursors(
    library_client: AsyncClient, test_database: tuple[str, str], signing_keys: LocalSigningKeys
) -> None:
    headers = {"Authorization": "Bearer " + signing_keys.token()}
    ids = [str(UUID(int=n)) for n in range(1, 5)]
    for id in ids:
        await seed_video(test_database, id=UUID(id), title="FAITH lesson")
    await seed_video(test_database, title="Unrelated")
    query = {"search": "faith", "status": "READY", "publication_status": "DRAFT", "limit": 2}
    first = await library_client.get("/v1/videos", params=query, headers=headers)
    assert first.status_code == 200
    assert [v["id"] for v in first.json()["data"]] == ids[::-1][:2]
    token = first.json()["pagination"]["next_page_token"]
    assert first.json()["pagination"]["has_more"] and token
    # Newer inserts must not shift the second page as offset pagination would.
    await seed_video(
        test_database, title="Faith newer", created_at=datetime(2026, 10, 17, tzinfo=UTC)
    )
    second = await library_client.get(
        "/v1/videos", params=query | {"cursor": token}, headers=headers
    )
    assert [v["id"] for v in second.json()["data"]] == ids[::-1][2:]
    assert second.json()["pagination"] == {"has_more": False, "next_page_token": None}
    for change in [
        {"search": "other"},
        {"status": "FAILED"},
        {"publication_status": "PUBLISHED"},
        {"limit": 1},
    ]:
        rejected = await library_client.get(
            "/v1/videos", params=query | {"cursor": token} | change, headers=headers
        )
        assert rejected.status_code == 400


async def test_viewer_filters_and_visibility_changed_cursor_are_rejected(
    library_client: AsyncClient, test_database: tuple[str, str], signing_keys: LocalSigningKeys
) -> None:
    for _ in range(2):
        await seed_video(test_database, published=True)
    for query in [{"status": "READY"}, {"publication_status": "PUBLISHED"}]:
        assert (await library_client.get("/v1/videos", params=query)).status_code == 403
    page = await library_client.get("/v1/videos", params={"limit": 1})
    token = page.json()["pagination"]["next_page_token"]
    assert token
    assert (
        await library_client.get(
            "/v1/videos",
            params={"limit": 1, "cursor": token},
            headers={"Authorization": "Bearer " + signing_keys.token()},
        )
    ).status_code == 400
    for malformed in ["", "not-a-cursor", "e30=", "A" * 3000]:
        response = await library_client.get("/v1/videos", params={"cursor": malformed})
        assert response.status_code == 400
        assert isinstance(response.json()["detail"], str)
    for limit in [0, 101]:
        response = await library_client.get("/v1/videos", params={"limit": limit})
        assert response.status_code == 422


async def test_title_search_treats_wildcards_as_literal_characters(
    library_client: AsyncClient, test_database: tuple[str, str]
) -> None:
    literal = await seed_video(test_database, title="100%_sure", published=True)
    await seed_video(test_database, title="Another video", published=True)
    response = await library_client.get("/v1/videos", params={"search": "%_"})
    assert [v["id"] for v in response.json()["data"]] == [literal]


async def test_publish_unpublish_and_admin_preview_use_configured_delivery_origin(
    library_client: AsyncClient,
    test_database: tuple[str, str],
    signing_keys: LocalSigningKeys,
    api_app: FastAPI,
) -> None:
    api_app.state.settings.cdn_origin = "https://showcase-media.test/"
    id = await seed_video(test_database, generated_status="FAILED")
    path = f"/v1/videos/{id}"
    headers = {"Authorization": "Bearer " + signing_keys.token()}
    assert (await library_client.get(path + "/playback")).status_code == 404
    preview = await library_client.get(path + "/playback", headers=headers)
    assert preview.status_code == 200
    assert preview.json() == {
        "video_id": id,
        "playback": {
            "type": "hls",
            "url": f"https://showcase-media.test/videos/{id}/hls/master.m3u8",
        },
    }
    updates = await gather(
        *(
            library_client.patch(path, headers=headers, json={"publication_status": "PUBLISHED"})
            for _ in range(2)
        )
    )
    assert all(response.status_code == 200 for response in updates)
    timestamp = updates[0].json()["published_at"]
    assert timestamp and timestamp == updates[1].json()["published_at"]
    assert updates[0].json()["thumbnail"] == {"status": "FAILED", "source": "NONE", "url": None}
    assert (await library_client.get(path)).json()["published_at"] == timestamp
    assert (await library_client.get(path + "/playback")).json() == preview.json()
    edited = await library_client.patch(path, headers=headers, json={"title": "Edited"})
    assert edited.json()["status"] == "READY"
    assert edited.json()["published_at"] == timestamp
    unpublished = await library_client.patch(
        path, headers=headers, json={"publication_status": "DRAFT"}
    )
    assert unpublished.status_code == 200 and unpublished.json()["published_at"] is None
    assert (await library_client.get(path)).status_code == 404
    assert (await library_client.get(path + "/playback")).status_code == 404
    assert (await library_client.get(path, headers=headers)).json()["title"] == "Edited"
    assert (await library_client.get(path + "/playback", headers=headers)).status_code == 200


@pytest.mark.parametrize(
    "status", ["CREATED", "UPLOADING", "QUEUED", "PROCESSING", "FAILED", "DELETING"]
)
async def test_only_ready_videos_publish_and_unready_admin_playback_is_rejected(
    library_client: AsyncClient,
    test_database: tuple[str, str],
    signing_keys: LocalSigningKeys,
    status: str,
) -> None:
    id = await seed_video(test_database, status=status)
    headers = {"Authorization": "Bearer " + signing_keys.token()}
    response = await library_client.patch(
        f"/v1/videos/{id}", headers=headers, json={"publication_status": "PUBLISHED"}
    )
    assert response.status_code == 409
    playback = await library_client.get(f"/v1/videos/{id}/playback", headers=headers)
    assert playback.status_code == (404 if status == "DELETING" else 409)
    detail = await library_client.get(f"/v1/videos/{id}", headers=headers)
    assert detail.json()["status"] == status
    assert detail.json()["publication_status"] == "DRAFT"
    assert detail.json()["published_at"] is None


@pytest.mark.parametrize(
    "generated_status,generated_key,custom_key,expected",
    [
        ("PENDING", None, None, {"status": "PENDING", "source": "NONE", "url": None}),
        ("FAILED", None, None, {"status": "FAILED", "source": "NONE", "url": None}),
        (
            "READY",
            "thumbs/generated.jpg",
            None,
            {
                "status": "READY",
                "source": "GENERATED",
                "url": "https://cdn.test/thumbs/generated.jpg",
            },
        ),
        (
            "READY",
            "thumbs/generated.jpg",
            "thumbs/custom image?#.webp",
            {
                "status": "READY",
                "source": "CUSTOM",
                "url": "https://cdn.test/thumbs/custom%20image%3F%23.webp",
            },
        ),
        (
            "FAILED",
            None,
            "thumbs/custom.png",
            {"status": "READY", "source": "CUSTOM", "url": "https://cdn.test/thumbs/custom.png"},
        ),
    ],
)
async def test_active_thumbnail_projection_in_detail_and_list(
    library_client: AsyncClient,
    test_database: tuple[str, str],
    api_app: FastAPI,
    generated_status: str,
    generated_key: str | None,
    custom_key: str | None,
    expected: dict[str, str | None],
) -> None:
    api_app.state.settings.cdn_origin = "https://cdn.test"
    id = await seed_video(
        test_database,
        published=True,
        generated_status=generated_status,
        generated_key=generated_key,
        custom_key=custom_key,
    )
    detail = await library_client.get(f"/v1/videos/{id}")
    assert detail.json()["thumbnail"] == expected
    page = await library_client.get("/v1/videos")
    assert page.json()["data"] == [detail.json()]
    assert "source_key" not in detail.json() and "playback_key" not in detail.json()
    assert "processing_error" not in detail.json()


async def test_administrator_can_inspect_sanitized_processing_failure(
    library_client: AsyncClient, test_database: tuple[str, str], signing_keys: LocalSigningKeys
) -> None:
    id = await seed_video(test_database, status="FAILED", error=True)
    headers = {"Authorization": "Bearer " + signing_keys.token()}
    detail = await library_client.get(f"/v1/videos/{id}", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["processing_error"] == {
        "code": "TRANSCODE_FAILED",
        "message": "Video processing failed.",
    }
    page = await library_client.get("/v1/videos", headers=headers)
    assert page.json()["data"] == [detail.json()]
    assert (await library_client.get(f"/v1/videos/{id}")).status_code == 404


async def test_preview_rechecks_current_role_and_anonymous_discovery_avoids_role_directory(
    library_client: AsyncClient, test_database: tuple[str, str], signing_keys: LocalSigningKeys
) -> None:
    draft = await seed_video(test_database)
    published = await seed_video(test_database, published=True)
    headers = {"Authorization": "Bearer " + signing_keys.token()}
    assert (
        await library_client.get(f"/v1/videos/{draft}/playback", headers=headers)
    ).status_code == 200
    url, schema = test_database
    async with await AsyncConnection.connect(url, autocommit=True) as connection:
        await connection.execute(
            sql.SQL("UPDATE {}.\"user\" SET role='user'").format(sql.Identifier(schema + "_auth"))
        )
        assert (
            await library_client.get(f"/v1/videos/{draft}/playback", headers=headers)
        ).status_code == 404
        await connection.execute(
            sql.SQL('DROP TABLE {}."user"').format(sql.Identifier(schema + "_auth"))
        )
    assert (
        await library_client.get(f"/v1/videos/{draft}/playback", headers=headers)
    ).status_code == 503
    assert (await library_client.get(f"/v1/videos/{published}/playback")).status_code == 200
    assert [v["id"] for v in (await library_client.get("/v1/videos")).json()["data"]] == [published]
    assert (await library_client.get(f"/v1/videos/{uuid4()}/playback")).status_code == 404
