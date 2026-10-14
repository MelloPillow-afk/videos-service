"""ASGI application factory and shared-resource lifecycle."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.config import Settings
from src.core.generated.registry import register
from src.repositories import Database


def create_app(settings: Settings | None = None) -> FastAPI:
    database = Database(settings or Settings())

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
        await database.connect()
        try:
            yield
        finally:
            await database.close()

    app = FastAPI(
        title="Videos service",
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    app.state.database = database
    register(app)
    return app
