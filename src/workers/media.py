"""Media worker: runs one video-processing or thumbnail job, then exits.

Usage: python -m src.workers.media <job_id>
"""

import asyncio
import logging
import sys
from uuid import UUID

from src.config import Settings
from src.providers import cloudflare
from src.repositories.connections import close_database, open_database
from src.services import media as media_service


async def run(job_id: UUID, settings: Settings) -> None:
    await open_database(settings)
    cloudflare.open_storage(settings)
    try:
        await media_service.run_job(job_id, settings)
    finally:
        cloudflare.close_storage()
        await close_database()


def main(arguments: list[str]) -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    if len(arguments) != 1:
        sys.exit("usage: python -m src.workers.media <job_id>")
    asyncio.run(run(UUID(arguments[0]), Settings()))


if __name__ == "__main__":
    main(sys.argv[1:])
