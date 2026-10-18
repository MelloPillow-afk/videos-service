"""Environment configuration for local development and deployed processes."""

from typing import Annotated, Literal, Self

from pydantic import BeforeValidator, Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


def _split_origins(value: object) -> object:
    if isinstance(value, str):
        return [origin.strip() for origin in value.split(",") if origin.strip()]
    return value


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # prod launches workers on Cloud Run; dev launches them locally.
    api_env: Literal["dev", "prod"] = "dev"

    database_url: SecretStr = SecretStr("postgresql://videos:videos@localhost:5432/videos_dev")
    db_schema: str = Field(default="public", pattern=r"^[a-z_][a-z0-9_]{0,62}$")
    db_pool_min_size: int = Field(default=1, ge=0)
    db_pool_max_size: int = Field(default=5, ge=1)
    db_pool_timeout_seconds: float = Field(default=5, gt=0)
    db_connect_timeout_seconds: int = Field(default=5, ge=2)
    db_statement_timeout_ms: int = Field(default=5000, ge=1)

    # Browser origins allowed to call the API, comma-separated.
    cors_allowed_origins: Annotated[list[str], NoDecode, BeforeValidator(_split_origins)] = [
        "http://localhost:5173"
    ]

    # Neon Auth: the issuer and audience are the Auth URL origin.
    auth_issuer: str | None = None
    auth_jwks_url: str | None = None
    auth_audience: str | None = None
    # Local development only: accept any bearer token as this subject.
    auth_disabled: bool = False
    auth_disabled_subject: str = Field(default="dev-user", min_length=1)

    # Cloudflare R2, or local SeaweedFS behind Caddy's HTTPS in development.
    r2_endpoint_url: str = "https://localhost:9443"
    r2_access_key_id: SecretStr = SecretStr("videos")
    r2_secret_access_key: SecretStr = SecretStr("videos-secret")
    # A CA bundle that signs the endpoint's certificate, for local HTTPS.
    r2_ca_bundle: str | None = None
    # Private uploads, and the processed media viewers fetch from MEDIA_BASE_URL.
    r2_raw_bucket: str = Field(default="videos-raw", min_length=1)
    r2_processed_bucket: str = Field(default="videos-processed", min_length=1)
    media_base_url: str = "https://localhost:9443/videos-processed"
    max_upload_bytes: int = Field(default=104_857_600, ge=1)
    max_thumbnail_bytes: int = Field(default=10_485_760, ge=1)
    upload_url_ttl_seconds: int = Field(default=900, ge=60, le=604_800)
    max_duration_seconds: float = Field(default=300, gt=0)

    # Cloud Run job that runs the worker; required in prod.
    gcp_project: str | None = None
    gcp_region: str | None = None
    worker_job_name: str | None = None

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

    @model_validator(mode="after")
    def validate_production_settings(self) -> Self:
        if self.api_env == "prod" and not (
            self.gcp_project and self.gcp_region and self.worker_job_name
        ):
            raise ValueError(
                "GCP_PROJECT, GCP_REGION, and WORKER_JOB_NAME are required when API_ENV=prod"
            )
        return self
