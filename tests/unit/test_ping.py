"""The health handler stays reachable without a database."""

import asyncio
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from psycopg_pool import PoolTimeout
from pydantic import SecretStr

from src.app import create_app
from src.config import Settings
from src.repositories.connections import db_connection


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
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/ping")
            assert response.status_code == 200
            assert response.json() == {"status": "ok"}
            assert (await client.get("/v1/videos")).status_code == 200
        try:
            async with db_connection():
                raise AssertionError("Unexpected database connection")
        except PoolTimeout:
            pass
    # Shutdown closes the shared pool.
    with pytest.raises(RuntimeError):
        db_connection()


def test_health_stays_at_root_and_documentation_remains_disabled() -> None:
    app = create_app(Settings(auth_disabled=True))
    paths = app.openapi()["paths"]
    assert "/ping" in paths
    assert "/v1/ping" not in paths
    assert paths["/ping"]["get"].get("security", []) == []
    assert app.docs_url is None
    assert app.redoc_url is None
    assert app.openapi_url is None
