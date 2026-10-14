"""Service-owned resource lifecycle. Add initialization and cleanup here."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    # Initialize resources here. Fresh mocks do not open database connections.
    try:
        yield
    finally:
        # Close service resources here, including when the application fails.
        pass
