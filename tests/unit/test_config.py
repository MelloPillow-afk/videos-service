"""Validate configuration mistakes before opening database resources."""

import pytest
from pydantic import SecretStr, ValidationError

from src.config import Settings


def test_invalid_pool_range_is_rejected() -> None:
    with pytest.raises(ValidationError, match="must not exceed"):
        Settings(db_pool_min_size=6, db_pool_max_size=5, auth_disabled=True)


@pytest.mark.parametrize("timeout", [0, -1])
def test_unbounded_timeouts_are_rejected(timeout: int) -> None:
    with pytest.raises(ValidationError, match="db_pool_timeout_seconds"):
        Settings(db_pool_timeout_seconds=timeout, auth_disabled=True)


@pytest.mark.parametrize("schema", ["public,other", "bad schema", "MixedCase", "x" * 64])
def test_unsafe_database_schema_is_rejected(schema: str) -> None:
    with pytest.raises(ValidationError, match="db_schema"):
        Settings(db_schema=schema, auth_disabled=True)


@pytest.mark.parametrize("url", ["mysql://videos@localhost/videos", "sqlite:///videos.db"])
def test_non_postgresql_database_url_is_rejected(url: str) -> None:
    with pytest.raises(ValidationError, match="PostgreSQL"):
        Settings(database_url=SecretStr(url), auth_disabled=True)


def test_prod_requires_the_worker_job() -> None:
    with pytest.raises(ValidationError, match="WORKER_JOB_NAME"):
        Settings(api_env="prod", gcp_project="p", gcp_region="r", auth_disabled=True)


def test_prod_refuses_disabled_auth() -> None:
    with pytest.raises(ValidationError, match="AUTH_DISABLED"):
        Settings(
            api_env="prod",
            gcp_project="p",
            gcp_region="r",
            worker_job_name="w",
            auth_disabled=True,
        )
