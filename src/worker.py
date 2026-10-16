"""Cloud Run job command adapter; use cases and execution policy live in services."""

import argparse
import asyncio
import json
from collections.abc import Awaitable, Callable, Sequence
from uuid import UUID

import httpx

from src.config import Settings
from src.domain.videos import VideoConflict
from src.providers.storage import Storage
from src.repositories.database import Database
from src.services import media_jobs


async def run_job(
    job_id: UUID,
    database: Database,
    storage: Storage,
    settings: Settings,
    *,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
) -> bool | None:
    """Compatibility entry point; None is a benign unclaimed or fenced execution."""
    return await media_jobs.run_job(job_id, database, storage, settings, sleep=sleep)


async def process_video(
    work: media_jobs.Work, database: Database, storage: Storage, settings: Settings
) -> bool:
    """Preserve the public processing seam while delegating the operation to its service."""
    return await media_jobs.process_video(work, database, storage, settings)


async def main_async(
    job_id: UUID,
    *,
    recover: bool = False,
    previous_execution_terminated: bool = False,
    storage: Storage | None = None,
    gcloud_auth: bool = False,
    job_transport: httpx.AsyncBaseTransport | None = None,
) -> bool | None:
    if gcloud_auth and not recover:
        raise ValueError("Local gcloud authentication is available only for recovery.")
    settings = Settings()
    # Import the configured cloud adapter only for the executable entry point.
    from src.providers.r2 import R2Storage

    database = Database(settings)
    await database.connect()
    try:
        if recover:
            from src.providers.cloud_run import CloudRunJobLauncher
            from src.services.job_recovery import JobSubmission

            return await JobSubmission(
                database,
                CloudRunJobLauncher(settings, transport=job_transport, gcloud_auth=gcloud_auth),
            ).recover(job_id, previous_execution_terminated=previous_execution_terminated)
        return await run_job(
            job_id, database, storage if storage is not None else R2Storage(settings), settings
        )
    finally:
        await database.close()


def main(
    arguments: Sequence[str] | None = None,
    *,
    storage: Storage | None = None,
    job_transport: httpx.AsyncBaseTransport | None = None,
) -> None:
    parser = argparse.ArgumentParser(
        description="Run one persisted media job; no periodic dispatcher."
    )
    subcommands = parser.add_subparsers(dest="command", required=True)
    run = subcommands.add_parser("run")
    run.add_argument("--job-id", type=UUID, required=True)
    recover = subcommands.add_parser(
        "recover", help="Explicitly relaunch recorded work; never resets an active claim silently."
    )
    recover.add_argument("--job-id", type=UUID, required=True)
    recover.add_argument(
        "--gcloud-auth",
        action="store_true",
        help="Use the local gcloud login explicitly for this recovery; default is runtime metadata identity.",
    )
    recover.add_argument(
        "--previous-execution-terminated",
        action="store_true",
        help="Operator confirms the previous execution is terminated; required for RUNNING claims.",
    )
    parsed = parser.parse_args(arguments)
    failure_message = "Job execution failed; inspect persisted state and provider execution."
    try:
        result = asyncio.run(
            main_async(
                parsed.job_id,
                recover=parsed.command == "recover",
                storage=storage,
                gcloud_auth=getattr(parsed, "gcloud_auth", False),
                job_transport=job_transport,
                previous_execution_terminated=getattr(
                    parsed, "previous_execution_terminated", False
                ),
            )
        )
    except VideoConflict as error:
        result = False
        failure_message = str(error)
    except Exception:
        # Provider/configuration exceptions can contain credentials. Persisted state
        # and provider execution evidence are the operator diagnostic boundaries.
        result = False
    print(
        json.dumps(
            {
                "job_id": str(parsed.job_id),
                "command": parsed.command,
                "outcome": "no_op" if result is None else "succeeded" if result else "failed",
            }
        )
    )
    if result is False:
        parser.exit(1, failure_message + "\n")


if __name__ == "__main__":
    main()
