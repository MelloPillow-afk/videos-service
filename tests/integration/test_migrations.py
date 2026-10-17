"""Apply and roll back migrations through Yoyo in an isolated PostgreSQL schema."""

import asyncio
import os
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import pytest
from psycopg import AsyncConnection

pytestmark = pytest.mark.integration


@pytest.mark.parametrize(
    ("sources", "tables"),
    [
        (Path(__file__).parent / "migrations", ["migration_probe"]),
        (Path(__file__).parents[2] / "migrations", ["jobs"]),
    ],
    ids=["probe", "service"],
)
async def test_yoyo_apply_and_rollback(
    test_database: tuple[str, str], tmp_path: Path, sources: Path, tables: list[str]
) -> None:
    url, schema = test_database
    config = tmp_path / "yoyo.ini"
    config.write_text(
        f"[DEFAULT]\nsources = {sources}\ndatabase = %(YOYO_DATABASE_URL)s\nbatch_mode = on\n"
    )
    parsed = urlsplit(url)
    parameters = dict(parse_qsl(parsed.query))
    parameters["schema"] = schema
    migration_url = urlunsplit(
        parsed._replace(scheme="postgresql+psycopg", query=urlencode(parameters))
    )
    environment = {**os.environ, "YOYO_DATABASE_URL": migration_url}

    async def run_yoyo(*command: str) -> None:
        process = await asyncio.create_subprocess_exec(
            "yoyo",
            "--config",
            str(config),
            *command,
            env=environment,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        async with asyncio.timeout(20):
            stdout, stderr = await process.communicate()
        assert process.returncode == 0, (stdout + stderr).decode()

    async def exists(table: str) -> bool:
        async with await AsyncConnection.connect(url, autocommit=True) as connection:
            cursor = await connection.execute("SELECT to_regclass(%s)", (f"{schema}.{table}",))
            row = await cursor.fetchone()
        return row is not None and row[0] is not None

    await run_yoyo("apply")
    await run_yoyo("apply")
    assert all([await exists(table) for table in tables])
    await run_yoyo("rollback", "--all")
    assert not any([await exists(table) for table in tables])
