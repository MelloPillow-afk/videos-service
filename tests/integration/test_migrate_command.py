"""Run the migration command the way `make migrate` does, against an isolated schema."""

import asyncio
import os
import sys
from pathlib import Path

import pytest
from psycopg import AsyncConnection

pytestmark = pytest.mark.integration

SERVICE_ROOT = Path(__file__).parents[2]


async def migrate(*command: str, cwd: Path, database_url: str) -> tuple[int, str]:
    environment = {
        **os.environ,
        "PYTHONPATH": str(SERVICE_ROOT),
        "DATABASE_URL": database_url,
        "AUTH_DISABLED": "true",
    }
    process = await asyncio.create_subprocess_exec(
        sys.executable,
        "-m",
        "src.repositories.migrate",
        *command,
        cwd=cwd,
        env=environment,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    async with asyncio.timeout(20):
        output, _ = await process.communicate()
    assert process.returncode is not None
    return process.returncode, output.decode()


async def test_apply_creates_service_tables_and_list_reports_them(
    test_database: tuple[str, str],
) -> None:
    url, schema = test_database
    database_url = f"{url}?options=-csearch_path%3D{schema}"

    code, output = await migrate("apply", cwd=SERVICE_ROOT, database_url=database_url)
    assert code == 0, output
    async with await AsyncConnection.connect(url, autocommit=True) as connection:
        cursor = await connection.execute("SELECT to_regclass(%s)", (f"{schema}.jobs",))
        assert await cursor.fetchone() == (f"{schema}.jobs",)

    code, output = await migrate("list", cwd=SERVICE_ROOT, database_url=database_url)
    assert code == 0, output
    assert "0001_jobs" in output


async def test_command_refuses_to_run_outside_the_service_root(tmp_path: Path) -> None:
    code, output = await migrate(
        "apply", cwd=tmp_path, database_url="postgresql://videos@localhost/unused"
    )
    assert code != 0
    assert "repository root" in output
