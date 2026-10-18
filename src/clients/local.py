"""Local development: runs each worker job in its own Docker Compose container."""

import subprocess
from pathlib import Path
from uuid import UUID

# The service root, where compose.yaml defines the worker.
_COMPOSE_DIRECTORY = Path(__file__).resolve().parents[2]


async def run_job(job_id: UUID) -> None:
    """Start the job's worker container, without waiting for it to finish.

    The worker's logs appear in this process's output.
    """
    subprocess.Popen(
        ["docker", "compose", "run", "--rm", "-T", "worker", str(job_id)],
        cwd=_COMPOSE_DIRECTORY,
        stdin=subprocess.DEVNULL,
    )
