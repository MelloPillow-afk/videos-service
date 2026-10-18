"""Browsers on the configured frontend origins may call the API; other origins may not."""

import pytest
from httpx import ASGITransport, AsyncClient, Response

from src.app import create_app
from src.config import Settings

FRONTEND = "https://sundays-best.pages.dev"
LOCAL = Settings(
    db_pool_min_size=0, auth_disabled=True, cors_allowed_origins=["http://localhost:5173"]
)


async def preflight(settings: Settings, origin: str) -> Response:
    app = create_app(settings)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        return await client.options(
            "/v1/admin/videos",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "authorization, content-type",
            },
        )


async def test_configured_origins_are_read_from_a_comma_separated_setting(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", f"http://localhost:5173, {FRONTEND}")
    settings = Settings(db_pool_min_size=0, auth_disabled=True)

    response = await preflight(settings, FRONTEND)

    assert response.status_code == 200
    assert response.headers["Access-Control-Allow-Origin"] == FRONTEND
    allowed = response.headers["Access-Control-Allow-Headers"].lower()
    assert {"authorization", "content-type"} <= {header.strip() for header in allowed.split(",")}
    assert "POST" in response.headers["Access-Control-Allow-Methods"]


async def test_other_origins_are_refused() -> None:
    response = await preflight(LOCAL, FRONTEND)

    assert response.status_code == 400
    assert "Access-Control-Allow-Origin" not in response.headers


async def test_browsers_can_read_the_location_header() -> None:
    app = create_app(LOCAL)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/ping", headers={"Origin": "http://localhost:5173"})

    assert response.headers["Access-Control-Allow-Origin"] == "http://localhost:5173"
    assert response.headers["Access-Control-Expose-Headers"] == "Location"
