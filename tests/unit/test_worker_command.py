"""The executable boundary never emits credential-bearing configuration errors."""

import json
import os
import subprocess
import sys
from uuid import uuid4


def test_configuration_failure_is_nonzero_and_redacted() -> None:
    secret = "private-connection-sentinel-never-log"
    result = subprocess.run(
        [sys.executable, "-m", "src.worker", "run", "--job-id", str(uuid4())],
        env={**os.environ, "DATABASE_URL": secret},
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1
    assert json.loads(result.stdout)["outcome"] == "failed"
    assert secret not in result.stdout + result.stderr
    assert "Traceback" not in result.stderr
