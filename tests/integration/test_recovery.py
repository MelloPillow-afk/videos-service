"""Recovery acceptance through HTTP, PostgreSQL and real media/provider boundaries."""

import asyncio
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from psycopg import AsyncConnection, sql

from src.config import Settings
from src.domain.videos import VideoConflict
from src.providers.storage import TemporaryStorageError
from src.services.job_recovery import JobSubmission
from src.worker import run_job
from tests.integration.test_processing import MediaStorage, make_source, seed_job
from tests.integration.test_processing import worker_client as worker_client
from tests.job_provider import RecordingLauncher
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


@pytest.fixture
def storage() -> IntermittentStorage:
    return IntermittentStorage(0)


async def test_transient_failure_retries_real_media_and_becomes_ready(
    worker_client: AsyncClient,
    api_app: FastAPI,
    signing_keys: LocalSigningKeys,
    test_database: tuple[str, str],
    tmp_path: Path,
    storage: IntermittentStorage,
) -> None:
    storage.failures = 1
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
    storage: IntermittentStorage,
) -> None:
    storage.failures = 10
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


async def test_explicit_retry_records_new_job_and_http_observes_queued_draft(
    worker_client: AsyncClient,
    api_app: FastAPI,
    signing_keys: LocalSigningKeys,
    test_database: tuple[str, str],
    tmp_path: Path,
    storage: IntermittentStorage,
) -> None:
    storage.failures = 10
    location, job_id = await seed_job(
        worker_client, signing_keys, test_database, storage, make_source(tmp_path / "source.mp4")
    )

    async def advance_time(delay: float) -> None:
        pass

    await run_job(job_id, api_app.state.database, storage, Settings(), sleep=advance_time)
    response = await worker_client.post(
        location + ":retry", headers={"Authorization": "Bearer " + signing_keys.token()}
    )
    assert response.status_code == 202
    assert response.json()["processing_job_id"] != str(job_id)
    assert response.json()["attempt"] == 2
    detail = await worker_client.get(
        location, headers={"Authorization": "Bearer " + signing_keys.token()}
    )
    assert detail.json()["status"] == "QUEUED"
    assert detail.json()["publication_status"] == "DRAFT"


async def test_concurrent_explicit_retries_create_one_current_job_and_one_launch(
    worker_client: AsyncClient,
    api_app: FastAPI,
    signing_keys: LocalSigningKeys,
    test_database: tuple[str, str],
    tmp_path: Path,
    storage: IntermittentStorage,
    launcher: RecordingLauncher,
) -> None:
    storage.failures = 10
    location, job_id = await seed_job(
        worker_client, signing_keys, test_database, storage, make_source(tmp_path / "source.mp4")
    )

    async def advance_time(delay: float) -> None:
        pass

    await run_job(job_id, api_app.state.database, storage, Settings(), sleep=advance_time)
    results = await asyncio.gather(
        *(
            worker_client.post(
                location + ":retry", headers={"Authorization": "Bearer " + signing_keys.token()}
            )
            for _ in range(2)
        )
    )
    assert sorted(response.status_code for response in results) == [202, 409]
    accepted = next(response.json() for response in results if response.status_code == 202)
    assert launcher.submissions == [UUID(accepted["processing_job_id"])]
    async with await AsyncConnection.connect(test_database[0]) as connection:
        row = await (
            await connection.execute(
                sql.SQL(
                    "SELECT count(*),count(*) FILTER(WHERE is_current) FROM {}.jobs WHERE kind='VIDEO'"
                ).format(sql.Identifier(test_database[1]))
            )
        ).fetchone()
    assert row == (2, 1)
    detail = (
        await worker_client.get(
            location, headers={"Authorization": "Bearer " + signing_keys.token()}
        )
    ).json()
    assert detail["status"] == "QUEUED" and detail["thumbnail"]["status"] == "PENDING"


async def test_invalid_source_cannot_be_explicitly_retried_or_replaced(
    worker_client: AsyncClient,
    api_app: FastAPI,
    signing_keys: LocalSigningKeys,
    test_database: tuple[str, str],
    storage: IntermittentStorage,
) -> None:
    location, job_id = await seed_job(
        worker_client, signing_keys, test_database, storage, b"corrupt"
    )
    await run_job(job_id, api_app.state.database, storage, Settings())
    response = await worker_client.post(
        location + ":retry", headers={"Authorization": "Bearer " + signing_keys.token()}
    )
    assert response.status_code == 409
    assert "deletion and recreation" in response.json()["detail"]
    assert (
        await worker_client.post(
            location + ":upload-url",
            headers={"Authorization": "Bearer " + signing_keys.token()},
            json={"file_name": "source.mp4", "content_type": "video/mp4", "size_bytes": 10},
        )
    ).status_code == 409


async def test_later_storage_failure_keeps_a_previously_validated_source_recoverable(
    worker_client: AsyncClient,
    api_app: FastAPI,
    signing_keys: LocalSigningKeys,
    test_database: tuple[str, str],
    tmp_path: Path,
) -> None:
    class ReadUnavailable(MediaStorage):
        async def read(self, area: str, key: str, max_bytes: int) -> bytes:
            raise TemporaryStorageError

    storage = ReadUnavailable()
    location, job_id = await seed_job(
        worker_client, signing_keys, test_database, storage, make_source(tmp_path / "source.mp4")
    )
    async with await AsyncConnection.connect(test_database[0], autocommit=True) as connection:
        await connection.execute(
            sql.SQL("UPDATE {}.videos SET source_validated=true").format(
                sql.Identifier(test_database[1])
            )
        )

    async def advance_time(delay: float) -> None:
        pass

    await run_job(job_id, api_app.state.database, storage, Settings(), sleep=advance_time)
    assert (
        await worker_client.get(
            location, headers={"Authorization": "Bearer " + signing_keys.token()}
        )
    ).json()["status"] == "FAILED"
    async with await AsyncConnection.connect(test_database[0]) as connection:
        row = await (
            await connection.execute(
                sql.SQL("SELECT source_validated FROM {}.videos").format(
                    sql.Identifier(test_database[1])
                )
            )
        ).fetchone()
    assert row == (True,)


async def test_manual_relaunch_submits_recorded_current_work_without_processing_inline(
    worker_client: AsyncClient,
    api_app: FastAPI,
    signing_keys: LocalSigningKeys,
    test_database: tuple[str, str],
    tmp_path: Path,
    storage: IntermittentStorage,
    launcher: RecordingLauncher,
) -> None:
    location, job_id = await seed_job(
        worker_client, signing_keys, test_database, storage, make_source(tmp_path / "source.mp4")
    )
    assert await JobSubmission(api_app.state.database, launcher).recover(job_id)
    assert launcher.submissions == [job_id]
    assert (
        await worker_client.get(
            location, headers={"Authorization": "Bearer " + signing_keys.token()}
        )
    ).json()["status"] == "QUEUED"
    async with await AsyncConnection.connect(test_database[0]) as connection:
        row = await (
            await connection.execute(
                sql.SQL("SELECT state,execution_attempts FROM {}.jobs WHERE id=%s").format(
                    sql.Identifier(test_database[1])
                ),
                (job_id,),
            )
        ).fetchone()
    assert row == ("LAUNCHED", 0)


@pytest.mark.parametrize("ineligible", ["deleting", "superseded"])
async def test_manual_relaunch_rejects_deleted_or_superseded_work(
    worker_client: AsyncClient,
    api_app: FastAPI,
    signing_keys: LocalSigningKeys,
    test_database: tuple[str, str],
    tmp_path: Path,
    storage: IntermittentStorage,
    launcher: RecordingLauncher,
    ineligible: str,
) -> None:
    _, job_id = await seed_job(
        worker_client, signing_keys, test_database, storage, make_source(tmp_path / "source.mp4")
    )
    async with await AsyncConnection.connect(test_database[0], autocommit=True) as connection:
        query = (
            "UPDATE {}.videos SET status='DELETING'"
            if ineligible == "deleting"
            else "UPDATE {}.jobs SET is_current=false"
        )
        await connection.execute(sql.SQL(query).format(sql.Identifier(test_database[1])))
    with pytest.raises(VideoConflict, match="superseded or ineligible"):
        await JobSubmission(api_app.state.database, launcher).recover(job_id)
    assert launcher.submissions == []


async def test_running_claim_requires_operator_confirmation_of_termination(
    worker_client: AsyncClient,
    api_app: FastAPI,
    signing_keys: LocalSigningKeys,
    test_database: tuple[str, str],
    tmp_path: Path,
    storage: IntermittentStorage,
    launcher: RecordingLauncher,
) -> None:
    location, job_id = await seed_job(
        worker_client, signing_keys, test_database, storage, make_source(tmp_path / "source.mp4")
    )
    async with await AsyncConnection.connect(test_database[0], autocommit=True) as connection:
        await connection.execute(
            sql.SQL(
                "UPDATE {}.jobs SET state='RUNNING',execution_attempts=1,claim_token=%s,updated_at='2000-01-01' WHERE id=%s"
            ).format(sql.Identifier(test_database[1])),
            (uuid4(), job_id),
        )
        await connection.execute(
            sql.SQL("UPDATE {}.videos SET status='PROCESSING'").format(
                sql.Identifier(test_database[1])
            )
        )
    with pytest.raises(VideoConflict, match="previous execution has terminated"):
        await JobSubmission(api_app.state.database, launcher).recover(job_id)
    assert launcher.submissions == []
    assert await JobSubmission(api_app.state.database, launcher).recover(
        job_id, previous_execution_terminated=True
    )
    assert await run_job(job_id, api_app.state.database, storage, Settings())
    assert (
        await worker_client.get(
            location, headers={"Authorization": "Bearer " + signing_keys.token()}
        )
    ).json()["status"] == "READY"
    async with await AsyncConnection.connect(test_database[0]) as connection:
        row = await (
            await connection.execute(
                sql.SQL(
                    "SELECT execution_attempts,execution_history FROM {}.jobs WHERE id=%s"
                ).format(sql.Identifier(test_database[1])),
                (job_id,),
            )
        ).fetchone()
    assert row is not None and row[0] == 2
    assert row[1][0]["state"] == "INTERRUPTED"


async def test_interrupted_final_execution_becomes_failed_without_a_fourth_execution(
    worker_client: AsyncClient,
    api_app: FastAPI,
    signing_keys: LocalSigningKeys,
    test_database: tuple[str, str],
    tmp_path: Path,
    storage: IntermittentStorage,
    launcher: RecordingLauncher,
) -> None:
    location, job_id = await seed_job(
        worker_client, signing_keys, test_database, storage, make_source(tmp_path / "source.mp4")
    )
    async with await AsyncConnection.connect(test_database[0], autocommit=True) as connection:
        await connection.execute(
            sql.SQL("UPDATE {}.jobs SET state='RUNNING',execution_attempts=3 WHERE id=%s").format(
                sql.Identifier(test_database[1])
            ),
            (job_id,),
        )
        await connection.execute(
            sql.SQL("UPDATE {}.videos SET status='PROCESSING',source_validated=true").format(
                sql.Identifier(test_database[1])
            )
        )
    with pytest.raises(VideoConflict, match="budget is exhausted"):
        await JobSubmission(api_app.state.database, launcher).recover(
            job_id, previous_execution_terminated=True
        )
    assert launcher.submissions == []
    assert (
        await worker_client.get(
            location, headers={"Authorization": "Bearer " + signing_keys.token()}
        )
    ).json()["status"] == "FAILED"
    assert (
        await worker_client.post(
            location + ":retry", headers={"Authorization": "Bearer " + signing_keys.token()}
        )
    ).status_code == 202


async def test_explicit_retry_requires_current_admin_and_failed_lifecycle(
    worker_client: AsyncClient,
    signing_keys: LocalSigningKeys,
    test_database: tuple[str, str],
) -> None:
    headers = {"Authorization": "Bearer " + signing_keys.token()}
    created = await worker_client.post("/v1/videos", json={"title": "Not failed"}, headers=headers)
    path = created.headers["Location"] + ":retry"
    assert (await worker_client.post(path)).status_code == 401
    assert (await worker_client.post(path, headers=headers)).status_code == 409
    assert (
        await worker_client.post("/v1/videos/not-a-uuid:retry", headers=headers)
    ).status_code == 422
    async with await AsyncConnection.connect(test_database[0], autocommit=True) as connection:
        await connection.execute(
            sql.SQL("UPDATE {}.\"user\" SET role='user'").format(
                sql.Identifier(test_database[1] + "_auth")
            )
        )
    assert (await worker_client.post(path, headers=headers)).status_code == 403


async def test_missing_retained_source_does_not_create_a_new_processing_job(
    worker_client: AsyncClient,
    api_app: FastAPI,
    signing_keys: LocalSigningKeys,
    test_database: tuple[str, str],
    tmp_path: Path,
    storage: IntermittentStorage,
    launcher: RecordingLauncher,
) -> None:
    storage.failures = 10
    location, job_id = await seed_job(
        worker_client, signing_keys, test_database, storage, make_source(tmp_path / "source.mp4")
    )

    async def advance_time(delay: float) -> None:
        pass

    await run_job(job_id, api_app.state.database, storage, Settings(), sleep=advance_time)
    storage.objects = {key: value for key, value in storage.objects.items() if key[0] != "private"}
    assert (
        await worker_client.post(
            location + ":retry", headers={"Authorization": "Bearer " + signing_keys.token()}
        )
    ).status_code == 409
    assert launcher.submissions == []
    async with await AsyncConnection.connect(test_database[0]) as connection:
        row = await (
            await connection.execute(
                sql.SQL("SELECT count(*) FROM {}.jobs").format(sql.Identifier(test_database[1]))
            )
        ).fetchone()
    assert row == (1,)


async def test_retry_launch_interruption_is_persisted_and_manually_relaunchable(
    worker_client: AsyncClient,
    api_app: FastAPI,
    signing_keys: LocalSigningKeys,
    test_database: tuple[str, str],
    tmp_path: Path,
    storage: IntermittentStorage,
    launcher: RecordingLauncher,
) -> None:
    storage.failures = 10
    location, job_id = await seed_job(
        worker_client, signing_keys, test_database, storage, make_source(tmp_path / "source.mp4")
    )

    async def advance_time(delay: float) -> None:
        pass

    await run_job(job_id, api_app.state.database, storage, Settings(), sleep=advance_time)
    launcher.fail = True
    response = await worker_client.post(
        location + ":retry", headers={"Authorization": "Bearer " + signing_keys.token()}
    )
    assert response.status_code == 202
    retry_id = UUID(response.json()["processing_job_id"])
    async with await AsyncConnection.connect(test_database[0]) as connection:
        row = await (
            await connection.execute(
                sql.SQL("SELECT state,error_code FROM {}.jobs WHERE id=%s").format(
                    sql.Identifier(test_database[1])
                ),
                (retry_id,),
            )
        ).fetchone()
    assert row == ("LAUNCH_FAILED", "LAUNCH_UNCONFIRMED")
    launcher.fail = False
    assert await JobSubmission(api_app.state.database, launcher).recover(retry_id)
    assert launcher.submissions == [retry_id, retry_id]


@pytest.mark.parametrize("state", ["SUCCEEDED", "FAILED"])
async def test_manual_relaunch_rejects_finished_jobs(
    worker_client: AsyncClient,
    api_app: FastAPI,
    signing_keys: LocalSigningKeys,
    test_database: tuple[str, str],
    tmp_path: Path,
    storage: IntermittentStorage,
    launcher: RecordingLauncher,
    state: str,
) -> None:
    _, job_id = await seed_job(
        worker_client, signing_keys, test_database, storage, make_source(tmp_path / "source.mp4")
    )
    async with await AsyncConnection.connect(test_database[0], autocommit=True) as connection:
        await connection.execute(
            sql.SQL("UPDATE {}.jobs SET state=%s WHERE id=%s").format(
                sql.Identifier(test_database[1])
            ),
            (state, job_id),
        )
    with pytest.raises(VideoConflict, match="Only stranded launches"):
        await JobSubmission(api_app.state.database, launcher).recover(job_id)
    assert launcher.submissions == []


async def test_deletion_during_backoff_prevents_another_media_execution(
    worker_client: AsyncClient,
    api_app: FastAPI,
    signing_keys: LocalSigningKeys,
    test_database: tuple[str, str],
    tmp_path: Path,
    storage: IntermittentStorage,
) -> None:
    storage.failures = 1
    location, job_id = await seed_job(
        worker_client, signing_keys, test_database, storage, make_source(tmp_path / "source.mp4")
    )

    async def delete_while_waiting(delay: float) -> None:
        response = await worker_client.delete(
            location, headers={"Authorization": "Bearer " + signing_keys.token()}
        )
        assert response.status_code == 202

    assert not await run_job(
        job_id, api_app.state.database, storage, Settings(), sleep=delete_while_waiting
    )
    assert (
        await worker_client.get(
            location, headers={"Authorization": "Bearer " + signing_keys.token()}
        )
    ).json()["status"] == "DELETING"
    async with await AsyncConnection.connect(test_database[0]) as connection:
        row = await (
            await connection.execute(
                sql.SQL("SELECT execution_attempts FROM {}.jobs WHERE id=%s").format(
                    sql.Identifier(test_database[1])
                ),
                (job_id,),
            )
        ).fetchone()
    assert row == (1,)


async def test_cleanup_relaunch_has_no_media_execution_cap_and_keeps_policy_diagnostic(
    worker_client: AsyncClient,
    api_app: FastAPI,
    signing_keys: LocalSigningKeys,
    test_database: tuple[str, str],
    launcher: RecordingLauncher,
) -> None:
    headers = {"Authorization": "Bearer " + signing_keys.token()}
    created = await worker_client.post("/v1/videos", json={"title": "Delete"}, headers=headers)
    location = created.headers["Location"]
    assert (await worker_client.delete(location, headers=headers)).status_code == 202
    async with await AsyncConnection.connect(test_database[0], autocommit=True) as connection:
        cursor = await connection.execute(
            sql.SQL(
                "UPDATE {}.jobs SET state='FAILED',execution_attempts=5 WHERE kind='DELETION' RETURNING id"
            ).format(sql.Identifier(test_database[1]))
        )
        row = await cursor.fetchone()
        assert row is not None
        job_id = row[0]
    assert await JobSubmission(api_app.state.database, launcher).recover(job_id)
    assert (await worker_client.get(location, headers=headers)).json()["status"] == "DELETING"
    async with await AsyncConnection.connect(test_database[0]) as connection:
        row = await (
            await connection.execute(
                sql.SQL(
                    "SELECT state,execution_attempts,error_code FROM {}.jobs WHERE id=%s"
                ).format(sql.Identifier(test_database[1])),
                (job_id,),
            )
        ).fetchone()
    assert row == ("LAUNCHED", 5, "CLEANUP_POLICY_REQUIRED")
