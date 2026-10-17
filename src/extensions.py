"""Service-owned resource lifecycle. Add initialization and cleanup here."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.clients import cloudflare, gcp
from src.config import Settings
from src.repositories.connections import close_database, open_database


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    settings: Settings = app.state.settings
    await open_database(settings)
    cloudflare.open_storage(settings)
    if settings.api_env == "prod":
        gcp.open_jobs(settings)
    try:
        yield
    finally:
        # Close service resources here, including when the application fails.
        await gcp.close_jobs()
        cloudflare.close_storage()
        await close_database()
