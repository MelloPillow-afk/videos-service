"""Database fixtures are shared in tests/conftest.py with generated HTTP tests."""

from collections.abc import AsyncIterator

import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient


@pytest_asyncio.fixture
async def client(api_app: FastAPI, api_bearer_token: str) -> AsyncIterator[AsyncClient]:
    """Authenticated client for the real application, with its lifespan running."""
    async with (
        api_app.router.lifespan_context(api_app),
        AsyncClient(
            transport=ASGITransport(app=api_app),
            base_url="http://test",
            headers={"Authorization": f"Bearer {api_bearer_token}"},
        ) as client,
    ):
        yield client
