"""Recovery acceptance through HTTP, PostgreSQL and real media/provider boundaries."""

from pathlib import Path

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from psycopg import AsyncConnection, sql

from src.config import Settings
from src.providers.storage import TemporaryStorageError
from src.worker import run_job
from tests.integration.test_processing import MediaStorage, make_source, seed_job
from tests.integration.test_processing import worker_client as worker_client
from tests.providers import LocalSigningKeys

pytestmark = pytest.mark.integration


class IntermittentStorage(MediaStorage):
    def __init__(self, failures: int) -> None:
        super().__init__()
        self.failures = failures

    async def write(
        self, area: str, key: str, data: bytes, content_type: str, *, create_only: bool = True
    ) -> None:
        if self.failures:
            self.failures -= 1
            raise TemporaryStorageError
        await super().write(area, key, data, content_type, create_only=create_only)


async def test_transient_failure_retries_real_media_and_becomes_ready(
    worker_client: AsyncClient,
    api_app: FastAPI,
    signing_keys: LocalSigningKeys,
    test_database: tuple[str, str],
    tmp_path: Path,
) -> None:
    storage = IntermittentStorage(1)
    location, job_id = await seed_job(
        worker_client, signing_keys, test_database, storage, make_source(tmp_path / "source.mp4")
    )

    delays: list[float] = []

    async def advance_time(delay: float) -> None:
        delays.append(delay)

    assert await run_job(job_id, api_app.state.database, storage, Settings(), sleep=advance_time)
    assert delays == [1]

    response = await worker_client.get(
        location, headers={"Authorization": "Bearer " + signing_keys.token()}
    )
    assert response.json()["status"] == "READY"
    async with await AsyncConnection.connect(test_database[0]) as connection:
        row = await (
            await connection.execute(
                sql.SQL("SELECT execution_attempts,output_keys FROM {}.jobs WHERE id=%s").format(
                    sql.Identifier(test_database[1])
                ),
                (job_id,),
            )
        ).fetchone()
    assert row is not None and row[0] == 2
    assert any("/attempt-1-" in key for key in row[1]) and any(
        "/attempt-2-" in key for key in row[1]
    )


async def test_three_temporary_executions_exhaust_with_increasing_delays_and_history(
    worker_client: AsyncClient,
    api_app: FastAPI,
    signing_keys: LocalSigningKeys,
    test_database: tuple[str, str],
    tmp_path: Path,
) -> None:
    storage = IntermittentStorage(10)
    location, job_id = await seed_job(
        worker_client, signing_keys, test_database, storage, make_source(tmp_path / "source.mp4")
    )
    delays: list[float] = []

    async def advance_time(delay: float) -> None:
        delays.append(delay)

    assert not await run_job(
        job_id, api_app.state.database, storage, Settings(), sleep=advance_time
    )
    assert delays == [1, 4]
    response = await worker_client.get(
        location, headers={"Authorization": "Bearer " + signing_keys.token()}
    )
    assert response.json()["status"] == "FAILED"
    async with await AsyncConnection.connect(test_database[0]) as connection:
        row = await (
            await connection.execute(
                sql.SQL(
                    "SELECT execution_attempts,execution_history,output_keys FROM {}.jobs WHERE id=%s"
                ).format(sql.Identifier(test_database[1])),
                (job_id,),
            )
        ).fetchone()
        video = await (
            await connection.execute(
                sql.SQL("SELECT source_validated FROM {}.videos").format(
                    sql.Identifier(test_database[1])
                )
            )
        ).fetchone()
    assert row is not None and row[0] == 3
    assert [event["state"] for event in row[1]] == [
        "RUNNING",
        "TEMPORARY_FAILURE",
        "RUNNING",
        "TEMPORARY_FAILURE",
        "RUNNING",
        "FAILED",
    ]
    assert all(any(f"/attempt-{number}-" in key for key in row[2]) for number in [1, 2, 3])
    assert video == (True,)


async def test_permanent_invalid_source_does_not_receive_execution_retries(
    worker_client: AsyncClient,
    api_app: FastAPI,
    signing_keys: LocalSigningKeys,
    test_database: tuple[str, str],
) -> None:
    storage = MediaStorage()
    _, job_id = await seed_job(worker_client, signing_keys, test_database, storage, b"corrupt")

    async def unexpected_delay(delay: float) -> None:
        pytest.fail("Permanent source rejection must not retry")

    assert not await run_job(
        job_id, api_app.state.database, storage, Settings(), sleep=unexpected_delay
    )
    async with await AsyncConnection.connect(test_database[0]) as connection:
        row = await (
            await connection.execute(
                sql.SQL("SELECT execution_attempts,error_code FROM {}.jobs WHERE id=%s").format(
                    sql.Identifier(test_database[1])
                ),
                (job_id,),
            )
        ).fetchone()
    assert row == (1, "INVALID_SOURCE")
