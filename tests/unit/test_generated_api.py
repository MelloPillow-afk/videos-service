"""The complete generated contract is available through native FastAPI HTTP routes."""

import pytest
from fastapi import HTTPException
from fastapi.routing import APIRoute
from httpx import ASGITransport, AsyncClient

from src.app import create_app
from src.config import Settings
from src.handlers.generated import (
    health,
    playback,
    thumbnails,
    videos,
)


async def test_invalid_video_id_uses_native_request_validation() -> None:
    app = create_app(Settings(db_pool_min_size=0))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/v1/videos/not-a-uuid")
    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["path", "id"]
    assert "error" not in response.json()


# Literal expectations follow the authoritative schema examples.
VIDEO_ID = "550e8400-e29b-41d4-a716-446655440000"
RESOURCE = f"/v1/videos/{VIDEO_ID}"
CUSTOM_THUMBNAIL = {
    "status": "READY",
    "source": "CUSTOM",
    "url": f"https://media.example.com/videos/{VIDEO_ID}/thumbnails/custom-v2.jpg",
}
SOURCE_UPLOAD_ID = "04d1790f-f941-4ba6-8d97-0e6830ca4394"
THUMBNAIL_UPLOAD_ID = "50fd0382-794f-4c9b-9a12-60e92a89e008"


async def test_unimplemented_operations_serve_exact_contract_examples() -> None:
    cases: list[tuple[str, str, dict[str, object] | None, int, dict[str, object]]] = [
        ("GET", "/ping", None, 200, {"status": "ok"}),
        ("DELETE", RESOURCE, None, 202, {"video_id": VIDEO_ID, "status": "DELETING"}),
        (
            "POST",
            f"{RESOURCE}/thumbnails:upload-url",
            {"file_name": "cover.jpg", "content_type": "image/jpeg", "size_bytes": 183420},
            200,
            {
                "video_id": VIDEO_ID,
                "upload": {
                    "upload_id": THUMBNAIL_UPLOAD_ID,
                    "method": "PUT",
                    "url": "https://uploads.example.com/thumbnail.jpg?signature=example",
                    "headers": {"Content-Type": "image/jpeg", "If-None-Match": "*"},
                    "expires_at": "2026-10-13T14:15:00Z",
                },
            },
        ),
        (
            "POST",
            f"{RESOURCE}/thumbnails:complete-upload",
            {"upload_id": THUMBNAIL_UPLOAD_ID},
            200,
            {"video_id": VIDEO_ID, "thumbnail": CUSTOM_THUMBNAIL},
        ),
        (
            "DELETE",
            f"{RESOURCE}/thumbnails",
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
        ("POST", f"{RESOURCE}:complete-upload", {"upload_id": "invalid"}),
        (
            "POST",
            f"{RESOURCE}:upload-url",
            {"file_name": "lesson.mp4", "content_type": "video/webm", "size_bytes": 5},
        ),
        (
            "POST",
            f"{RESOURCE}/thumbnails:upload-url",
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


async def test_native_query_parsing_and_exact_collection_path() -> None:
    app = create_app(Settings(db_pool_min_size=0))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            "/v1/videos?limit=2&status=READY&publication_status=PUBLISHED&search=faith&cursor=next"
        )
        assert response.status_code == 403
        assert response.json() == {"detail": "Administrator access is required for these filters."}
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


def test_generated_routes_keep_runtime_settings_without_contract_documentation() -> None:
    modules = (health, playback, thumbnails, videos)
    routes = [
        route for module in modules for route in module.router.routes if isinstance(route, APIRoute)
    ]
    assert len(routes) == 13
    for route in routes:
        assert route.response_model is not None
        assert route.response_model_exclude_unset is True
        assert route.operation_id is None
        assert route.tags == []
        assert route.summary is None
        assert route.description == ""
        assert route.deprecated is None
        assert route.responses == {}
        assert route.openapi_extra is None
