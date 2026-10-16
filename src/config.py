"""Environment configuration for local development and deployed processes."""

from typing import Self

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: SecretStr = SecretStr("postgresql://videos:videos@localhost:5432/videos_dev")
    db_schema: str = Field(default="public", pattern=r"^[a-z_][a-z0-9_]{0,62}$")
    db_pool_min_size: int = Field(default=1, ge=0)
    db_pool_max_size: int = Field(default=5, ge=1)
    db_pool_timeout_seconds: float = Field(default=5, gt=0)
    db_connect_timeout_seconds: int = Field(default=5, ge=2)
    db_statement_timeout_ms: int = Field(default=5000, ge=1)

    # Neon Auth: the issuer and audience are the Auth URL origin.
    auth_issuer: str | None = None
    auth_jwks_url: str | None = None
    auth_audience: str | None = None
    # Local development only: accept any bearer token as this subject.
    auth_disabled: bool = False
    auth_disabled_subject: str = Field(default="dev-user", min_length=1)

    @model_validator(mode="after")
    def validate_database_settings(self) -> Self:
        if self.db_pool_min_size > self.db_pool_max_size:
            raise ValueError("DB_POOL_MIN_SIZE must not exceed DB_POOL_MAX_SIZE")
        if not self.database_url.get_secret_value().startswith(("postgresql://", "postgres://")):
            raise ValueError("DATABASE_URL must be a PostgreSQL connection URL")
        return self

    @model_validator(mode="after")
    def validate_auth_settings(self) -> Self:
        if not self.auth_disabled and not (
            self.auth_issuer and self.auth_jwks_url and self.auth_audience
        ):
            raise ValueError(
                "AUTH_ISSUER, AUTH_JWKS_URL, and AUTH_AUDIENCE are required "
                "unless AUTH_DISABLED=true"
            )
        return self
