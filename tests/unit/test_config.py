"""Validate configuration mistakes before opening database resources."""

import pytest
from pydantic import ValidationError

from src.config import Settings


def test_settings_read_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DB_POOL_MIN_SIZE", "2")
    monkeypatch.setenv("DB_POOL_MAX_SIZE", "4")
    monkeypatch.setenv("AUTH_DISABLED", "true")
    settings = Settings()
    assert settings.db_pool_min_size == 2
    assert settings.db_pool_max_size == 4
    assert settings.db_pool_timeout_seconds > 0


def test_invalid_pool_range_is_rejected() -> None:
    with pytest.raises(ValidationError, match="must not exceed"):
        Settings(db_pool_min_size=6, db_pool_max_size=5)


@pytest.mark.parametrize("timeout", [0, -1])
def test_unbounded_timeouts_are_rejected(timeout: int) -> None:
    with pytest.raises(ValidationError):
        Settings(db_pool_timeout_seconds=timeout)


@pytest.mark.parametrize("schema", ["public,other", "bad schema", "MixedCase", "x" * 64])
def test_unsafe_database_schema_is_rejected(schema: str) -> None:
    with pytest.raises(ValidationError):
        Settings(db_schema=schema)
