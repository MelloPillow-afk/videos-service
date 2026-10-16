"""Local operator credentials stay an explicit external CLI/provider boundary."""

import json
import os
from pathlib import Path
from uuid import uuid4

import httpx
import pytest

from src.config import Settings
from src.providers.cloud_run import CloudRunJobLauncher
from src.providers.jobs import JobLaunchError
from src.worker import main


async def test_gcloud_opt_in_uses_only_explicit_cli_identity_for_job_request(
    gcloud_cli: Path,
) -> None:
    job_id = uuid4()
    requests: list[httpx.Request] = []

    async def respond(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        assert request.method == "POST"
        assert (
            str(request.url)
            == "https://run.googleapis.com/v2/projects/target/locations/region/jobs/media:run"
        )
        assert request.headers["Authorization"] == "Bearer controlled-operator-access-token"
        return httpx.Response(
            200, json={"name": "projects/target/locations/region/operations/recovery"}
        )

    launcher = CloudRunJobLauncher(
        Settings(cloud_run_job_resource="projects/target/locations/region/jobs/media"),
        transport=httpx.MockTransport(respond),
        gcloud_auth=True,
    )
    assert await launcher.launch(job_id) == "projects/target/locations/region/operations/recovery"
    assert len(requests) == 1
    assert json.loads(gcloud_cli.read_text())["args"] == ["auth", "print-access-token", "--quiet"]
    assert json.loads(requests[0].content)["overrides"]["containerOverrides"][0]["args"] == [
        "run",
        "--job-id",
        str(job_id),
    ]


@pytest.mark.parametrize("mode", ["failed", "empty", "missing", "timeout"])
async def test_operator_auth_errors_are_redacted_and_timeout_reaps_child(
    gcloud_cli: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    mode: str,
) -> None:
    if mode == "failed":
        monkeypatch.setenv("TEST_GCLOUD_EXIT", "1")
    elif mode == "empty":
        monkeypatch.setenv("TEST_GCLOUD_EMPTY", "1")
    elif mode == "missing":
        monkeypatch.setenv("PATH", str(gcloud_cli.parent / "missing"))
    else:
        monkeypatch.setenv("TEST_GCLOUD_DELAY", "10")

    async def forbidden(_: httpx.Request) -> httpx.Response:
        pytest.fail("No job request is permitted without confirmed operator credentials")

    launcher = CloudRunJobLauncher(
        Settings(cloud_run_job_resource="projects/target/locations/region/jobs/media"),
        transport=httpx.MockTransport(forbidden),
        gcloud_auth=True,
        # Allow the real helper interpreter to start under AMD64 emulation;
        # its ten-second delay still requires timeout termination and reaping.
        auth_timeout_seconds=2,
    )
    with pytest.raises(JobLaunchError, match="Operator authentication was unavailable") as error:
        await launcher.launch(uuid4())
    output = capsys.readouterr()
    assert "controlled-" not in str(error.value) + output.out + output.err
    if mode == "timeout":
        pid = json.loads(gcloud_cli.read_text())["pid"]
        with pytest.raises(ProcessLookupError):
            os.kill(pid, 0)


@pytest.mark.parametrize("metadata_available", [True, False])
async def test_runtime_default_uses_metadata_and_never_falls_back_to_installed_gcloud(
    gcloud_cli: Path,
    metadata_available: bool,
) -> None:
    requests: list[httpx.Request] = []

    async def respond(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.host == "metadata.google.internal":
            assert request.headers["Metadata-Flavor"] == "Google"
            return (
                httpx.Response(200, json={"access_token": "controlled-runtime-token"})
                if metadata_available
                else httpx.Response(503)
            )
        assert request.headers["Authorization"] == "Bearer controlled-runtime-token"
        return httpx.Response(200, json={"name": "projects/target/operations/runtime"})

    launcher = CloudRunJobLauncher(
        Settings(cloud_run_job_resource="projects/target/locations/region/jobs/media"),
        transport=httpx.MockTransport(respond),
    )
    if metadata_available:
        assert await launcher.launch(uuid4()) == "projects/target/operations/runtime"
    else:
        with pytest.raises(JobLaunchError):
            await launcher.launch(uuid4())
    assert len(requests) == (2 if metadata_available else 1)
    assert not gcloud_cli.exists()


def test_gcloud_flag_is_rejected_for_media_run(
    gcloud_cli: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as error:
        main(["run", "--job-id", str(uuid4()), "--gcloud-auth"])
    assert error.value.code == 2
    assert "--gcloud-auth" in capsys.readouterr().err
    assert not gcloud_cli.exists()
