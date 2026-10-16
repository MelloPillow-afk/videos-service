"""Bounded explicit cleanup executions retain permanent guards and permit manual recovery."""

import asyncio
from collections.abc import Awaitable, Callable
from uuid import UUID, uuid4

from src.config import Settings
from src.domain.videos import VideoNotFound
from src.providers.storage import (
    GUARD_CONTENT_TYPE,
    GuardStorage,
    Storage,
    StorageArea,
    StorageConflictError,
    StorageMissingError,
    TemporaryStorageError,
)
from src.repositories import cleanup as repository
from src.repositories.cleanup import CleanupWork
from src.repositories.database import Database
from src.services.cleanup_inspection import inspect_cleanup


async def protect_inventory(
    work: CleanupWork, database: Database, storage: GuardStorage, settings: Settings
) -> bool:
    protected: set[tuple[StorageArea, str]] = set()
    while True:
        async with asyncio.timeout(settings.media_provider_timeout_seconds):
            inventory = await inspect_cleanup(database, work.id, storage)
        keys: set[tuple[StorageArea, str]] = {("private", key) for key in inventory.private_keys}
        keys.update(("public", key) for key in inventory.public_keys)
        for area, key in sorted(keys - protected):
            async with database.connection() as connection:
                if not await repository.eligible(connection, work):
                    return False
            async with asyncio.timeout(settings.media_provider_timeout_seconds):
                await storage.seal(area, key)
            protected.add((area, key))
        # Verify the entire finite manifest, including keys that never existed. Listings
        # discover legacy objects; their emptiness never substitutes for the manifest.
        for area, key in sorted(keys):
            async with asyncio.timeout(settings.media_provider_timeout_seconds):
                observed = await storage.head(area, key)
            if (
                observed is None
                or observed.size_bytes != 0
                or not observed.deletion_guard
                or observed.content_type != GUARD_CONTENT_TYPE
            ):
                raise TemporaryStorageError
        async with asyncio.timeout(settings.media_provider_timeout_seconds):
            final = await inspect_cleanup(database, work.id, storage)
        final_keys: set[tuple[StorageArea, str]] = {("private", key) for key in final.private_keys}
        final_keys.update(("public", key) for key in final.public_keys)
        if final_keys <= protected:
            async with database.connection() as connection:
                return await repository.complete(connection, work)
        # No new registered writes are permitted after DELETING. This pass also
        # closes discovery of pre-existing legacy keys during the first listing.


async def run_cleanup(
    job_id: UUID,
    database: Database,
    storage: Storage,
    settings: Settings,
    *,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
) -> bool | None:
    async with database.connection() as connection:
        work = await repository.claim(connection, job_id, uuid4())
    if work is None:
        return None
    try:
        async with asyncio.timeout(settings.cleanup_runtime_seconds):
            retry_index = 0
            while True:
                try:
                    if not isinstance(storage, GuardStorage):
                        raise TemporaryStorageError
                    return (
                        True if await protect_inventory(work, database, storage, settings) else None
                    )
                except VideoNotFound:
                    return None
                except (
                    TemporaryStorageError,
                    StorageConflictError,
                    StorageMissingError,
                    TimeoutError,
                    OSError,
                ):
                    async with database.connection() as connection:
                        if not await repository.failure(connection, work, terminal=False):
                            return None
                    delays = settings.cleanup_retry_delays_seconds
                    await sleep(delays[min(retry_index, len(delays) - 1)])
                    retry_index += 1
                    async with database.connection() as connection:
                        following = await repository.next_attempt(connection, work)
                    if following is None:
                        return None
                    work = following
    except TimeoutError:
        async with database.connection() as connection:
            applied = await repository.failure(connection, work, terminal=True)
        return False if applied else None
