"""Cloud Run-compatible direct job entry point and current-attempt worker orchestration."""

import argparse
import asyncio
import tempfile
from pathlib import Path
from uuid import UUID, uuid4

from src.config import Settings
from src.providers.storage import (
    Storage,
    StorageConflictError,
    StorageLimitError,
    StorageMissingError,
    TemporaryStorageError,
)
from src.repositories.database import Database
from src.repositories.workers import claim, complete, eligible, fail, register_outputs
from src.services.media import InvalidMedia, MediaProcessingError, encode_hls, validate_source


async def run_job(job_id: UUID, database: Database, storage: Storage, settings: Settings) -> bool:
    """Claim once, encode outside transactions, then conditionally publish verified assets."""
    async with database.connection() as connection:
        work = await claim(connection, job_id, uuid4())
    if work is None:
        return False
    validated = False
    try:
        async with asyncio.timeout(settings.media_provider_timeout_seconds):
            source = await storage.read("private", work.source_key, settings.source_max_bytes)
        if not source or len(source) > settings.source_max_bytes:
            raise InvalidMedia("The source exceeds the configured byte limit or is empty.")
        with tempfile.TemporaryDirectory(prefix="videos-worker-") as temporary:
            source_path = Path(temporary) / "source.mp4"
            source_path.write_bytes(source)
            info = await asyncio.to_thread(validate_source, source_path, settings)
            validated = True
            result = await asyncio.to_thread(
                encode_hls, source_path, Path(temporary) / "hls", settings, info
            )
            prefix = f"{work.output_prefix.rstrip('/')}/attempt-{work.attempt}-{work.token}/"
            keys = [prefix + path.name for path in result.files]
            # Commit the complete finite manifest before the first immutable object PUT.
            async with database.connection() as connection:
                if not await register_outputs(connection, work, keys):
                    return False
            for path, key in zip(result.files, keys, strict=True):
                async with database.connection() as connection:
                    if not await eligible(connection, work):
                        return False
                async with asyncio.timeout(settings.media_provider_timeout_seconds):
                    await storage.write(
                        "public",
                        key,
                        path.read_bytes(),
                        "application/vnd.apple.mpegurl" if path.suffix == ".m3u8" else "video/mp2t",
                        create_only=True,
                    )
            for path, key in zip(result.files, keys, strict=True):
                async with asyncio.timeout(settings.media_provider_timeout_seconds):
                    observed = await storage.head("public", key)
                if observed is None or observed.size_bytes != path.stat().st_size:
                    raise TemporaryStorageError
            async with database.connection() as connection:
                return await complete(
                    connection,
                    work,
                    prefix + result.master.name,
                    float(result.info.duration),
                    result.info.width,
                    result.info.height,
                )
    except (InvalidMedia, StorageLimitError) as error:
        message = (
            str(error)
            if isinstance(error, InvalidMedia)
            else "The source exceeds the configured byte limit."
        )
        async with database.connection() as connection:
            await fail(connection, work, "INVALID_SOURCE", message)
    except (
        MediaProcessingError,
        TemporaryStorageError,
        StorageMissingError,
        StorageConflictError,
        TimeoutError,
        OSError,
    ):
        async with database.connection() as connection:
            await fail(
                connection,
                work,
                "PROCESSING_FAILED",
                "Video processing could not be completed.",
                source_validated=validated,
            )
    return False


async def main_async(job_id: UUID) -> bool:
    settings = Settings()
    # Import the configured cloud adapter only for the executable entry point.
    from src.providers.r2 import R2Storage

    database = Database(settings)
    await database.connect()
    try:
        return await run_job(job_id, database, R2Storage(settings), settings)
    finally:
        await database.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run one persisted media job; no periodic dispatcher."
    )
    subcommands = parser.add_subparsers(dest="command", required=True)
    run = subcommands.add_parser("run")
    run.add_argument("--job-id", type=UUID, required=True)
    arguments = parser.parse_args()
    asyncio.run(main_async(arguments.job_id))


if __name__ == "__main__":
    main()
