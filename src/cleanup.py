"""Operator-only read-only cleanup inventory; explicit workers own completion."""

import argparse
import asyncio
import json
from dataclasses import asdict
from uuid import UUID

from psycopg import Error as DatabaseError

from src.config import Settings
from src.domain.videos import VideoNotFound
from src.providers.r2 import R2Storage
from src.providers.storage import TemporaryStorageError
from src.repositories.database import Database
from src.services.cleanup_inspection import inspect_cleanup


async def inspect(job_id: UUID, *, list_storage: bool) -> int:
    settings = Settings()
    database = Database(settings)
    await database.connect()
    try:
        inventory = await inspect_cleanup(
            database, job_id, R2Storage(settings) if list_storage else None
        )
        print(json.dumps(asdict(inventory), default=str, sort_keys=True))
        return 0
    except VideoNotFound:
        print("No current deletion job was found for a deleting video.")
    except (TemporaryStorageError, DatabaseError):
        print("Cleanup inspection is unavailable; no cleanup was performed.")
    finally:
        await database.close()
    return 2


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Inspect cleanup inputs; never remove media or records."
    )
    commands = parser.add_subparsers(dest="command", required=True)
    inspection = commands.add_parser("inspect")
    inspection.add_argument("--job-id", type=UUID, required=True)
    inspection.add_argument("--list-storage", action="store_true")
    args = parser.parse_args()
    raise SystemExit(asyncio.run(inspect(args.job_id, list_storage=args.list_storage)))


if __name__ == "__main__":
    main()
