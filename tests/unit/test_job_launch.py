"""Jobs launch on Cloud Run in prod and locally in dev."""

from types import ModuleType
from uuid import uuid4

import pytest

from src.clients import gcp, local
from src.config import Settings
from src.services import jobs as jobs_service
from tests.utilities.fakes import FakeLauncher

DEV = Settings(auth_disabled=True)
PROD = Settings(
    auth_disabled=True, api_env="prod", gcp_project="p", gcp_region="r", worker_job_name="w"
)


@pytest.mark.parametrize(("settings", "client"), [(DEV, local), (PROD, gcp)])
async def test_launch_uses_the_environment_launcher(
    monkeypatch: pytest.MonkeyPatch, settings: Settings, client: ModuleType
) -> None:
    used = FakeLauncher()
    monkeypatch.setattr(client, "run_job", used.run_job)
    job_id = uuid4()

    await jobs_service.launch(job_id, settings)

    assert used.launched == [job_id]
