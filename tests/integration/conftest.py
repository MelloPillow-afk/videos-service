"""Database fixtures are shared in tests/conftest.py with generated HTTP tests."""

from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import AsyncClient

from tests.api_client import running
from tests.media_files import make_video


@pytest_asyncio.fixture
async def client(api_app: FastAPI, api_bearer_token: str) -> AsyncIterator[AsyncClient]:
    async with running(api_app, api_bearer_token) as client:
        yield client


@pytest.fixture(scope="session")
def landscape_mp4(tmp_path_factory: pytest.TempPathFactory) -> bytes:
    """A 2-second 720p MP4 with audio."""
    return make_video(tmp_path_factory.mktemp("media") / "landscape.mp4", "1280x720", 2)
