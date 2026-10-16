"""Environment configuration for local development and deployed processes."""

import math
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

    auth_issuer: str | None = None
    auth_jwks_url: str | None = None
    auth_audience: str | None = None
    auth_schema: str = Field(default="neon_auth", pattern=r"^[a-z_][a-z0-9_]{0,62}$")
    source_max_bytes: int = Field(default=104857600, ge=1)
    source_max_duration_seconds: float = Field(default=300, gt=0)
    thumbnail_max_bytes: int = Field(default=5242880, ge=1)
    cdn_origin: str = "https://media.example.com"

    r2_endpoint_url: str | None = None
    r2_access_key_id: SecretStr | None = None
    r2_secret_access_key: SecretStr | None = None
    r2_private_bucket: str | None = None
    r2_public_bucket: str | None = None
    cloud_run_job_resource: str | None = Field(
        default=None, pattern=r"^projects/[^/]+/locations/[^/]+/jobs/[^/]+$"
    )

    ffmpeg_binary: str = "ffmpeg"
    ffprobe_binary: str = "ffprobe"
    media_retry_delays_seconds: tuple[float, float] = (1, 4)
    media_threads: int = Field(default=2, ge=1, le=8)
    media_probe_timeout_seconds: float = Field(default=30, gt=0)
    media_decode_timeout_seconds: float = Field(default=300, gt=0)
    media_encode_timeout_seconds: float = Field(default=900, gt=0)
    media_provider_timeout_seconds: float = Field(default=60, gt=0)
    media_output_max_bytes: int = Field(default=1073741824, ge=1)
    media_max_dimension: int = Field(default=8192, ge=2)
    media_max_pixels: int = Field(default=8294400, ge=4)

    @model_validator(mode="after")
    def validate_database_settings(self) -> Self:
        if (
            not all(math.isfinite(delay) for delay in self.media_retry_delays_seconds)
            or not 0 <= self.media_retry_delays_seconds[0] < self.media_retry_delays_seconds[1]
        ):
            raise ValueError("Media retry delays must be nonnegative and increasing.")
        if self.db_pool_min_size > self.db_pool_max_size:
            raise ValueError("DB_POOL_MIN_SIZE must not exceed DB_POOL_MAX_SIZE")
        if not self.database_url.get_secret_value().startswith(("postgresql://", "postgres://")):
            raise ValueError("DATABASE_URL must be a PostgreSQL connection URL")
        if self.r2_private_bucket and self.r2_private_bucket == self.r2_public_bucket:
            raise ValueError("R2 private and public buckets must differ")
        return self
