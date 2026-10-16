"""ASGI application factory and shared-resource lifecycle."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.config import Settings
from src.core.generated.routers import register_routers
from src.providers.auth import DisabledAuth, NeonIdentity, SigningKeys
from src.repositories import Database


def create_app(
    settings: Settings | None = None, *, signing_keys: SigningKeys | None = None
) -> FastAPI:
    settings = settings or Settings()
    database = Database(settings)

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
    app.state.authenticator = (
        DisabledAuth(settings.auth_disabled_subject)
        if settings.auth_disabled
        else NeonIdentity(settings, signing_keys)
    )
    register_routers(app)
    return app
