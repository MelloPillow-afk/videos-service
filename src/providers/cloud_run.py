"""Cloud Run v2 direct submission using the deployed service's metadata identity."""

from uuid import UUID

import httpx

from src.config import Settings
from src.providers.jobs import JobLaunchError


class CloudRunJobLauncher:
    def __init__(
        self, settings: Settings, *, transport: httpx.AsyncBaseTransport | None = None
    ) -> None:
        self.settings, self.transport = settings, transport

    async def launch(self, job_id: UUID) -> str:
        resource = self.settings.cloud_run_job_resource
        if resource is None:
            raise JobLaunchError("Job launch is unavailable.")
        try:
            async with httpx.AsyncClient(
                transport=self.transport, timeout=10, trust_env=False
            ) as client:
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
