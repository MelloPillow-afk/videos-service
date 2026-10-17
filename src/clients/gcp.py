"""Google Cloud Run: starts executions of the worker job.

Authenticates with Application Default Credentials, so the API's service account needs
permission to run the worker job with overrides.
"""

from uuid import UUID

from google.cloud import run_v2

from src.config import Settings

_client: run_v2.JobsAsyncClient | None = None
_job_name: str | None = None


def open_jobs(settings: Settings) -> None:
    """Create the process-wide Cloud Run client; the lifespan calls this in prod."""
    global _client, _job_name
    assert settings.gcp_project and settings.gcp_region and settings.worker_job_name
    _client = run_v2.JobsAsyncClient()
    _job_name = run_v2.JobsAsyncClient.job_path(
        settings.gcp_project, settings.gcp_region, settings.worker_job_name
    )


async def close_jobs() -> None:
    global _client, _job_name
    if _client is not None:
        await _client.transport.close()
    _client, _job_name = None, None


async def run_job(job_id: UUID) -> None:
    """Start a worker execution for the job, without waiting for it to finish."""
    if _client is None or _job_name is None:
        raise RuntimeError("Cloud Run is not open; it opens in the application lifespan")
    container = run_v2.RunJobRequest.Overrides.ContainerOverride(args=[str(job_id)])
    # The returned operation tracks the execution, which nothing here waits for.
    await _client.run_job(  # pyright: ignore[reportUnknownMemberType]
        request=run_v2.RunJobRequest(
            name=_job_name,
            overrides=run_v2.RunJobRequest.Overrides(container_overrides=[container]),
        )
    )
