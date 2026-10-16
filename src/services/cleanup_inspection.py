"""Read-only inspection never treats empty listings or URL expiry as writer drain."""

from dataclasses import replace
from uuid import UUID

from src.domain.deletion import CleanupInventory
from src.domain.videos import VideoNotFound
from src.providers.storage import Storage
from src.repositories.database import Database
from src.repositories.deletion import cleanup_inventory


async def inspect_cleanup(
    database: Database, job_id: UUID, storage: Storage | None = None
) -> CleanupInventory:
    async with database.connection() as connection:
        inventory = await cleanup_inventory(connection, job_id)
    if inventory is None:
        raise VideoNotFound
    if storage is None:
        return inventory
    private, public = set(inventory.private_keys), set(inventory.public_keys)
    # Listings can discover legacy/failed objects. They are not evidence that an
    # earlier ambiguous write has drained or that a finite manifest is complete.
    for prefix in inventory.prefixes:
        private.update(await storage.list("private", prefix))
        public.update(await storage.list("public", prefix))
    return replace(
        inventory,
        private_keys=tuple(sorted(private)),
        public_keys=tuple(sorted(public)),
        storage_listed=True,
    )
