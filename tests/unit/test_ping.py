"""The health route stays reachable without a database; documentation stays private."""

import asyncio
from pathlib import Path
from uuid import uuid4

from httpx import ASGITransport, AsyncClient
from pydantic import SecretStr

from src.app import create_app
from src.config import Settings


async def test_ping_remains_available_while_database_is_unreachable(tmp_path: Path) -> None:
    # This empty directory cannot contain a running PostgreSQL socket.
    settings = Settings(
        database_url=SecretStr(f"postgresql://videos:videos@/videos_test?host={tmp_path}"),
        db_pool_min_size=1,
        db_pool_timeout_seconds=0.05,
        auth_disabled=True,
    )
    app = create_app(settings)
    async with asyncio.timeout(2), app.router.lifespan_context(app):
        async with AsyncClient(
            transport=ASGITransport(app=app, raise_app_exceptions=False),
            base_url="http://test",
            headers={"Authorization": "Bearer local"},
        ) as client:
            response = await client.get("/ping")
            assert response.status_code == 200
            assert response.json() == {"status": "ok"}
            # Database-backed routes fail without revealing why.
            response = await client.get(f"/v1/admin/jobs/{uuid4()}")
            assert response.status_code == 500
            assert response.text == "Internal Server Error"


async def test_health_stays_at_root_and_documentation_remains_disabled() -> None:
    app = create_app(Settings(db_pool_min_size=0, auth_disabled=True))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        assert (await client.get("/ping")).status_code == 200
        for path in ("/v1/ping", "/docs", "/redoc", "/openapi.json"):
            assert (await client.get(path)).status_code == 404, path
