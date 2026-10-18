"""Drive the real application over HTTP."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient


@asynccontextmanager
async def running(app: FastAPI, bearer_token: str) -> AsyncGenerator[AsyncClient]:
    """Authenticated client for the real application, with its lifespan running."""
    async with (
        app.router.lifespan_context(app),
        AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            headers={"Authorization": f"Bearer {bearer_token}"},
        ) as client,
    ):
        yield client
