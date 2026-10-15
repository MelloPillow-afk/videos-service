"""The complete generated contract is available through native FastAPI HTTP routes."""

import pytest
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient

from src.app import create_app
from src.config import Settings


async def test_invalid_video_id_uses_native_request_validation() -> None:
    app = create_app(Settings(db_pool_min_size=0))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/v1/videos/not-a-uuid")
    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["path", "id"]
    assert "error" not in response.json()


# Literal expectations follow the approved contract examples, including the
# reusable ready-draft response that differs from the Video schema example.
VIDEO_ID = "550e8400-e29b-41d4-a716-446655440000"
RESOURCE = f"/v1/videos/{VIDEO_ID}"
CREATED: dict[str, object] = {
    "id": VIDEO_ID,
    "title": "Introduction to Faith",
    "description": "An introductory lesson",
    "status": "CREATED",
    "publication_status": "DRAFT",
    "size_bytes": None,
    "duration_seconds": None,
    "thumbnail": {"status": "PENDING", "source": "NONE", "url": None},
    "published_at": None,
    "created_at": "2026-10-13T14:00:00Z",
    "updated_at": "2026-10-13T14:00:00Z",
}
GENERATED_THUMBNAIL = {
    "status": "READY",
    "source": "GENERATED",
    "url": f"https://media.example.com/videos/{VIDEO_ID}/thumbnails/generated.jpg",
}
CUSTOM_THUMBNAIL = {
    "status": "READY",
    "source": "CUSTOM",
    "url": f"https://media.example.com/videos/{VIDEO_ID}/thumbnails/custom-v2.jpg",
}
READY: dict[str, object] = {
    **CREATED,
    "status": "READY",
    "size_bytes": 524288000,
    "duration_seconds": 1475.5,
    "thumbnail": GENERATED_THUMBNAIL,
    "updated_at": "2026-10-13T14:05:00Z",
}
PUBLISHED: dict[str, object] = {
    **READY,
    "publication_status": "PUBLISHED",
    "thumbnail": CUSTOM_THUMBNAIL,
    "published_at": "2026-10-13T15:00:00Z",
    "updated_at": "2026-10-13T15:00:00Z",
}
COLLECTION: dict[str, object] = {
    "data": [PUBLISHED],
    "pagination": {"has_more": True, "next_page_token": "example_next_page_token"},
}
SOURCE_UPLOAD_ID = "04d1790f-f941-4ba6-8d97-0e6830ca4394"
THUMBNAIL_UPLOAD_ID = "50fd0382-794f-4c9b-9a12-60e92a89e008"


async def test_all_thirteen_operations_serve_exact_contract_examples() -> None:
    cases: list[tuple[str, str, dict[str, object] | None, int, dict[str, object]]] = [
        ("GET", "/ping", None, 200, {"status": "ok"}),
        ("GET", "/v1/videos", None, 200, COLLECTION),
        ("POST", "/v1/videos", {"title": "A new video"}, 201, CREATED),
        ("GET", RESOURCE, None, 200, READY),
        ("PATCH", RESOURCE, {"title": "Updated title"}, 200, READY),
        ("DELETE", RESOURCE, None, 202, {"video_id": VIDEO_ID, "status": "DELETING"}),
        (
            "POST",
            f"{RESOURCE}/upload-url",
            {"file_name": "lesson.mp4", "content_type": "video/mp4", "size_bytes": 524288000},
            200,
            {
                "video_id": VIDEO_ID,
                "status": "UPLOADING",
                "upload": {
                    "upload_id": SOURCE_UPLOAD_ID,
                    "method": "PUT",
                    "url": "https://uploads.example.com/source.mp4?signature=example",
                    "headers": {"Content-Type": "video/mp4"},
                    "expires_at": "2026-10-13T14:15:00Z",
                },
            },
        ),
        (
            "POST",
            f"{RESOURCE}/complete-upload",
            {"upload_id": SOURCE_UPLOAD_ID},
            202,
            {
                "video_id": VIDEO_ID,
                "status": "QUEUED",
                "processing_job_id": "e9f1c6d0-4e8b-4a23-a52a-21a3d51127d0",
                "thumbnail_status": "PENDING",
            },
        ),
        (
            "GET",
            f"{RESOURCE}/playback",
            None,
            200,
            {
                "video_id": VIDEO_ID,
                "playback": {
                    "type": "hls",
                    "url": "https://media.example.com/videos/intro/hls/master.m3u8",
                },
            },
        ),
        (
            "POST",
            f"{RESOURCE}/retry",
            None,
            202,
            {
                "video_id": VIDEO_ID,
                "status": "QUEUED",
                "attempt": 2,
                "processing_job_id": "ac9afc7e-d6d1-4b5d-b0f2-fdb591862ea5",
            },
        ),
        (
            "POST",
            f"{RESOURCE}/thumbnail/upload-url",
            {"file_name": "cover.jpg", "content_type": "image/jpeg", "size_bytes": 183420},
            200,
            {
                "video_id": VIDEO_ID,
                "upload": {
                    "upload_id": THUMBNAIL_UPLOAD_ID,
                    "method": "PUT",
                    "url": "https://uploads.example.com/thumbnail.jpg?signature=example",
                    "headers": {"Content-Type": "image/jpeg"},
                    "expires_at": "2026-10-13T14:15:00Z",
                },
            },
        ),
        (
            "POST",
            f"{RESOURCE}/thumbnail/complete-upload",
            {"upload_id": THUMBNAIL_UPLOAD_ID},
            200,
            {"video_id": VIDEO_ID, "thumbnail": CUSTOM_THUMBNAIL},
        ),
        (
            "DELETE",
            f"{RESOURCE}/thumbnail",
            None,
            200,
            {"video_id": VIDEO_ID, "thumbnail": CUSTOM_THUMBNAIL},
        ),
    ]
    app = create_app(Settings(db_pool_min_size=0))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        for method, path, body, status, expected in cases:
            response = await client.request(method, path, json=body)
            assert response.status_code == status, (method, path, response.text)
            assert not response.history
            assert response.json() == expected, (method, path)
            if status == 201:
                assert response.headers["Location"] == RESOURCE


@pytest.mark.parametrize(
    ("method", "path", "body"),
    [
        ("GET", "/v1/videos?limit=0", None),
        ("GET", "/v1/videos?limit=101", None),
        ("GET", "/v1/videos?limit=many", None),
        ("GET", "/v1/videos?publication_status=UNKNOWN", None),
        ("GET", "/v1/videos?status=UNKNOWN", None),
        ("GET", f"/v1/videos?search={'x' * 201}", None),
        ("POST", "/v1/videos", None),
        ("POST", "/v1/videos", {}),
        ("POST", "/v1/videos", {"title": " "}),
        ("POST", "/v1/videos", {"title": "x" * 201}),
        ("POST", "/v1/videos", {"title": None}),
        ("PATCH", RESOURCE, {}),
        ("PATCH", RESOURCE, {"unknown": "value"}),
        ("PATCH", RESOURCE, {"title": None}),
        ("PATCH", RESOURCE, {"publication_status": "UNKNOWN"}),
        ("POST", f"{RESOURCE}/complete-upload", {"upload_id": "invalid"}),
        (
            "POST",
            f"{RESOURCE}/upload-url",
            {"file_name": "lesson.mp4", "content_type": "video/webm", "size_bytes": 5},
        ),
        (
            "POST",
            f"{RESOURCE}/thumbnail/upload-url",
            {"file_name": "cover.jpg", "content_type": "image/jpeg", "size_bytes": 0},
        ),
    ],
)
async def test_invalid_requests_use_native_validation(
    method: str, path: str, body: dict[str, object] | None
) -> None:
    app = create_app(Settings(db_pool_min_size=0))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.request(method, path, json=body)
    assert response.status_code == 422, response.text
    assert isinstance(response.json()["detail"], list)
    assert "error" not in response.json()


async def test_native_query_parsing_and_nullable_updates_are_accepted() -> None:
    app = create_app(Settings(db_pool_min_size=0))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            "/v1/videos?limit=2&status=READY&publication_status=PUBLISHED&search=faith&cursor=next"
        )
        assert response.status_code == 200
        assert response.json() == COLLECTION
        for body in [{"description": None}, {"title": "Renamed"}]:
            response = await client.patch(RESOURCE, json=body)
            assert response.status_code == 200
            assert response.json() == READY
        # The collection route preserves its exact contract spelling.
        response = await client.get("/v1/videos/")
        assert response.status_code == 307
        assert response.headers["Location"] == "http://test/v1/videos"


async def test_application_routes_keep_native_errors_and_preserved_lifecycle() -> None:
    app = create_app(Settings(db_pool_min_size=0))

    @app.get("/deliberate")
    async def deliberate() -> None:
        raise HTTPException(status_code=409, detail="The video is not ready.")

    @app.get("/unexpected")
    async def unexpected() -> None:
        raise RuntimeError("private exception detail")

    async with app.router.lifespan_context(app):
        async with AsyncClient(
            transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://test"
        ) as client:
            response = await client.get("/deliberate")
            assert response.status_code == 409
            assert response.json() == {"detail": "The video is not ready."}
            response = await client.get("/unexpected")
            assert response.status_code == 500
            assert response.headers["Content-Type"].startswith("text/plain")
            assert response.text == "Internal Server Error"
            assert (await client.get("/ping")).json() == {"status": "ok"}
            assert (await client.get("/docs")).status_code == 404
            assert (await client.get("/openapi.json")).status_code == 404


def test_response_documentation_describes_native_errors_and_original_tags() -> None:
    paths = create_app(Settings(db_pool_min_size=0)).openapi()["paths"]
    operation = paths["/v1/videos"]["post"]
    responses = operation["responses"]
    validation = responses["422"]["content"]["application/json"]["schema"]
    assert validation["properties"]["detail"]["type"] == "array"
    deliberate = responses["400"]["content"]["application/json"]["schema"]
    assert deliberate["properties"]["detail"]["type"] == "string"
    assert responses["500"]["content"]["text/plain"]["schema"]["type"] == "string"
    assert operation["tags"] == ["Videos"]
    assert paths["/v1/videos/{id}/upload-url"]["post"]["tags"] == ["Uploads"]
