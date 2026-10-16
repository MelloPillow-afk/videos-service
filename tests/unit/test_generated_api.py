"""The complete generated contract is available through native FastAPI HTTP routes."""

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
SOURCE_UPLOAD_ID = "04d1790f-f941-4ba6-8d97-0e6830ca4394"


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
