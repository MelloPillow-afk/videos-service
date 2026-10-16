"""Independent generated thumbnail execution, outside long database transactions."""

import asyncio
import tempfile
from pathlib import Path

from src.config import Settings
from src.providers.storage import Storage, TemporaryStorageError
from src.repositories.database import Database
from src.repositories.thumbnail_worker import complete
from src.repositories.workers import Work, eligible, register_outputs
from src.services.media import InvalidMedia
from src.services.thumbnail_media import extract_thumbnail


async def process(work: Work, database: Database, storage: Storage, settings: Settings) -> bool:
    async with asyncio.timeout(settings.media_provider_timeout_seconds):
        source = await storage.read("private", work.source_key, settings.source_max_bytes)
    if not source or len(source) > settings.source_max_bytes:
        raise InvalidMedia("The source exceeds the configured byte limit or is empty.")
    with tempfile.TemporaryDirectory(prefix="videos-thumbnail-") as directory:
        original = Path(directory) / "source.mp4"
        original.write_bytes(source)
        image = await asyncio.to_thread(
            extract_thumbnail, original, Path(directory) / "generated.jpg", settings
        )
        data = image.read_bytes()
    key = f"{work.output_prefix.rstrip('/')}/attempt-{work.attempt}-{work.token}/generated.jpg"
    async with database.connection() as connection:
        if not await register_outputs(connection, work, [key]):
            return False
    async with database.connection() as connection:
        if not await eligible(connection, work):
            return False
    async with asyncio.timeout(settings.media_provider_timeout_seconds):
        await storage.write("public", key, data, "image/jpeg", create_only=True)
        observed = await storage.head("public", key)
        if observed is None or observed.size_bytes != len(data):
            raise TemporaryStorageError
        if await storage.read("public", key, settings.thumbnail_max_bytes) != data:
            raise TemporaryStorageError
    async with database.connection() as connection:
        return await complete(connection, work, key)
