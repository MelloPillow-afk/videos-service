"""Service-owned resource lifecycle. Add initialization and cleanup here."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.repositories.connections import close_database, open_database


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    await open_database(app.state.settings)
    try:
        yield
    finally:
        # Close service resources here, including when the application fails.
        await close_database()
