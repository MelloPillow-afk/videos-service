"""Storage and Cloud Run clients make the right outgoing calls, without the network."""

import subprocess
from collections.abc import Iterator
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlsplit
from uuid import uuid4

import boto3
import pytest
from botocore.stub import Stubber
from google.cloud import run_v2

from src.clients import cloudflare, gcp

# Imported before the autouse fixtures replace them with fakes.
from src.clients.cloudflare import presign_upload, uploaded_size
from src.clients.gcp import run_job
from src.clients.local import run_job as local_run_job
from src.config import Settings


@pytest.fixture
def stubbed_r2(monkeypatch: pytest.MonkeyPatch) -> Iterator[Stubber]:
    cloudflare.open_storage(Settings(auth_disabled=True, media_base_url="https://media.test/"))
    client = boto3.client(  # pyright: ignore[reportUnknownMemberType]
        "s3",
        endpoint_url="http://r2.test",
        aws_access_key_id="key",
        aws_secret_access_key="secret",
        region_name="auto",
    )
    monkeypatch.setattr(cloudflare, "_client", client)
    with Stubber(client) as stubber:
        yield stubber
    cloudflare.close_storage()


def test_upload_url_signs_a_put_to_the_raw_bucket() -> None:
    cloudflare.open_storage(Settings(auth_disabled=True, upload_url_ttl_seconds=600))
    try:
        upload = presign_upload("videos/v/uploads/u/source.mp4", "video/mp4")
    finally:
        cloudflare.close_storage()

    url = urlsplit(upload.url)
    assert f"{url.scheme}://{url.netloc}{url.path}" == (
        "https://localhost:9443/videos-raw/videos/v/uploads/u/source.mp4"
    )
    query = parse_qs(url.query)
    assert query["X-Amz-Expires"] == ["600"]
    assert "content-type" in query["X-Amz-SignedHeaders"][0]


async def test_uploaded_size_reads_the_stored_object(stubbed_r2: Stubber) -> None:
    stubbed_r2.add_response(
        "head_object", {"ContentLength": 2048}, {"Bucket": "videos-raw", "Key": "a.mp4"}
    )

    assert await uploaded_size("a.mp4") == 2048


async def test_uploaded_size_of_a_missing_object_is_none(stubbed_r2: Stubber) -> None:
    stubbed_r2.add_client_error("head_object", service_error_code="404", http_status_code=404)

    assert await uploaded_size("a.mp4") is None


async def test_other_storage_errors_propagate(stubbed_r2: Stubber) -> None:
    stubbed_r2.add_client_error("head_object", service_error_code="403", http_status_code=403)

    with pytest.raises(Exception, match="403"):
        await uploaded_size("a.mp4")


def test_media_url_joins_the_public_origin_and_key(stubbed_r2: Stubber) -> None:
    assert (
        cloudflare.media_url("videos/v/thumbnail.jpg")
        == "https://media.test/videos/v/thumbnail.jpg"
    )


def test_storage_must_be_open() -> None:
    with pytest.raises(RuntimeError, match="Storage is not open"):
        cloudflare.media_url("key")


class RecordingJobsClient:
    def __init__(self) -> None:
        self.requests: list[Any] = []

    async def run_job(self, *, request: Any) -> None:
        self.requests.append(request)


async def test_run_job_starts_the_worker_with_the_job_id(monkeypatch: pytest.MonkeyPatch) -> None:
    client = RecordingJobsClient()
    monkeypatch.setattr(gcp, "_client", client)
    monkeypatch.setattr(gcp, "_job_name", "projects/p/locations/r/jobs/worker")
    job_id = uuid4()

    await run_job(job_id)

    (request,) = client.requests
    assert request == run_v2.RunJobRequest(
        name="projects/p/locations/r/jobs/worker",
        overrides=run_v2.RunJobRequest.Overrides(
            container_overrides=[
                run_v2.RunJobRequest.Overrides.ContainerOverride(args=[str(job_id)])
            ]
        ),
    )


async def test_cloud_run_must_be_open() -> None:
    with pytest.raises(RuntimeError, match="Cloud Run is not open"):
        await run_job(uuid4())


async def test_local_run_job_starts_a_compose_worker(monkeypatch: pytest.MonkeyPatch) -> None:
    started: list[tuple[list[str], dict[str, Any]]] = []

    def popen(command: list[str], **options: Any) -> None:
        started.append((command, options))

    monkeypatch.setattr(subprocess, "Popen", popen)
    job_id = uuid4()

    await local_run_job(job_id)

    ((command, options),) = started
    assert command == ["docker", "compose", "run", "--rm", "-T", "worker", str(job_id)]
    assert (Path(options["cwd"]) / "compose.yaml").is_file()
