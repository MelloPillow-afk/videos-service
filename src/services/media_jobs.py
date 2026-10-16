"""Persisted media-job orchestration and service-owned execution policy."""

import asyncio
import tempfile
from collections.abc import Awaitable, Callable
from pathlib import Path
from uuid import UUID, uuid4

from src.config import Settings
from src.domain.jobs import TemporaryWorkFailure
from src.providers.storage import (
    Storage,
    StorageConflictError,
    StorageLimitError,
    StorageMissingError,
    TemporaryStorageError,
)
from src.repositories.database import Database
from src.repositories.jobs import job_kind
from src.repositories.workers import (
    Work,
    claim,
    complete,
    eligible,
    fail,
    next_attempt,
    register_outputs,
)
from src.services.cleanup import run_cleanup
from src.services.media import InvalidMedia, MediaProcessingError, encode_hls, validate_source


async def run_job(
    job_id: UUID,
    database: Database,
    storage: Storage,
    settings: Settings,
    *,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
) -> bool | None:
    """True completed, False failed, None unclaimed/fenced; each execution owns its budget."""
    async with database.connection() as connection:
        kind = await job_kind(connection, job_id)
    if kind == "DELETION":
        return await run_cleanup(job_id, database, storage, settings, sleep=sleep)
    async with database.connection() as connection:
        if kind not in ("VIDEO", "THUMBNAIL"):
            return None
        work = await claim(connection, job_id, uuid4(), kind=kind)
    processor = process_video
    if kind == "THUMBNAIL":
        from src.services.thumbnail_worker import process

        processor = process
    while work is not None:
        try:
            return True if await processor(work, database, storage, settings) else None
        except (InvalidMedia, StorageLimitError) as error:
            message = (
                str(error)
                if isinstance(error, InvalidMedia)
                else "The source exceeds the configured byte limit."
            )
            async with database.connection() as connection:
                outcome = await fail(
                    connection, work, "INVALID_SOURCE", message, retry=False, invalidate_source=True
                )
            return False if outcome is not None else None
        except (
            TemporaryWorkFailure,
            MediaProcessingError,
            TemporaryStorageError,
            StorageMissingError,
            StorageConflictError,
            TimeoutError,
            OSError,
        ) as error:
            retry = work.attempt < 3
            async with database.connection() as connection:
                outcome = await fail(
                    connection,
                    work,
                    "PROCESSING_FAILED",
                    "Media processing could not be completed.",
                    source_validated=isinstance(error, TemporaryWorkFailure)
                    and error.source_validated,
                    retry=retry,
                )
            if outcome is not True:
                return outcome
            await sleep(settings.media_retry_delays_seconds[work.attempt - 1])
            async with database.connection() as connection:
                work = await next_attempt(connection, work, uuid4())
    return None


async def process_video(
    work: Work, database: Database, storage: Storage, settings: Settings
) -> bool:
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
                    float(result.duration),
                    result.info.width,
                    result.info.height,
                )
    except (InvalidMedia, StorageLimitError):
        raise
    except (
        MediaProcessingError,
        TemporaryStorageError,
        StorageMissingError,
        StorageConflictError,
        TimeoutError,
        OSError,
    ):
        raise TemporaryWorkFailure(source_validated=validated) from None
