"""Cloud Run submission; local operator identity requires an explicit opt-in."""

import asyncio
from uuid import UUID

import httpx

from src.config import Settings
from src.providers.jobs import JobLaunchError


async def gcloud_access_token(timeout_seconds: float = 10) -> str:
    """Capture only the installed CLI's token; never surface its stdout/stderr."""
    try:
        process = await asyncio.create_subprocess_exec(
            "gcloud",
            "auth",
            "print-access-token",
            "--quiet",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            async with asyncio.timeout(timeout_seconds):
                output, _ = await process.communicate()
        finally:
            if process.returncode is None:
                try:
                    process.kill()
                except ProcessLookupError:
                    pass
                await process.communicate()
        token = output.decode("ascii").strip()
        if (
            process.returncode != 0
            or not token
            or len(token) > 16384
            or any(c.isspace() for c in token)
        ):
            raise JobLaunchError("Operator authentication was unavailable.")
        return token
    except (OSError, TimeoutError, UnicodeError):
        raise JobLaunchError("Operator authentication was unavailable.") from None


class CloudRunJobLauncher:
    def __init__(
        self,
        settings: Settings,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
        gcloud_auth: bool = False,
        auth_timeout_seconds: float = 10,
    ) -> None:
        self.settings, self.transport = settings, transport
        self.gcloud_auth, self.auth_timeout_seconds = gcloud_auth, auth_timeout_seconds

    async def launch(self, job_id: UUID) -> str:
        resource = self.settings.cloud_run_job_resource
        if resource is None:
            raise JobLaunchError("Job launch is unavailable.")
        try:
            async with httpx.AsyncClient(
                transport=self.transport, timeout=10, trust_env=False
            ) as client:
                if self.gcloud_auth:
                    token = await gcloud_access_token(self.auth_timeout_seconds)
                else:
                    identity = await client.get(
                        "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token",
                        headers={"Metadata-Flavor": "Google"},
                    )
                    identity.raise_for_status()
                    token = identity.json()["access_token"]
                response = await client.post(
                    f"https://run.googleapis.com/v2/{resource}:run",
                    headers={"Authorization": f"Bearer {token}"},
                    json={
                        "overrides": {
                            "containerOverrides": [{"args": ["run", "--job-id", str(job_id)]}],
                            "taskCount": 1,
                            "timeout": "1200s",
                        }
                    },
                )
                response.raise_for_status()
                reference = response.json()["name"]
                if not isinstance(reference, str) or not reference:
                    raise ValueError
                return reference
        except (httpx.HTTPError, KeyError, ValueError, TypeError):
            raise JobLaunchError("Job submission was not confirmed.") from None
