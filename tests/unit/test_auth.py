"""Neon Auth verification, fail-fast configuration, and bearer enforcement over HTTP."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import jwt
import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient, Response
from jwt import PyJWK
from pydantic import SecretStr

from src.app import create_app
from src.clients.auth import SigningKeys
from src.config import Settings
from tests.auth_provider import AUTH_SETTINGS, LocalSigningKeys

VIDEO = "/v1/admin/videos/550e8400-e29b-41d4-a716-446655440000"
CATALOG = "/v1/videos"
RENAME = {"title": "Renamed"}


@pytest.fixture
def keys() -> LocalSigningKeys:
    return LocalSigningKeys()


def neon_app(keys: SigningKeys, **settings: Any) -> FastAPI:
    return create_app(Settings(db_pool_min_size=0, **AUTH_SETTINGS, **settings), signing_keys=keys)


async def rename(app: FastAPI, token: str | None) -> Response:
    headers = {} if token is None else {"Authorization": f"Bearer {token}"}
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.patch(VIDEO, json=RENAME, headers=headers)


@pytest.mark.parametrize(
    "claims",
    [
        {"seconds": -60},
        {"issuer": "https://other.test"},
        {"audience": "https://other.test"},
        {"kid": "unknown"},
        {"subject": ""},
        {"subject": 42},
    ],
)
async def test_untrusted_tokens_are_rejected(
    keys: LocalSigningKeys, claims: dict[str, Any]
) -> None:
    response = await rename(neon_app(keys), keys.token(**claims))
    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == 'Bearer error="invalid_token"'


@pytest.mark.parametrize("token", ["not-a-jwt", LocalSigningKeys().token()])
async def test_tokens_from_other_keys_are_rejected(keys: LocalSigningKeys, token: str) -> None:
    response = await rename(neon_app(keys), token)
    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == 'Bearer error="invalid_token"'


async def test_unreachable_jwks_is_unavailable(keys: LocalSigningKeys) -> None:
    class UnreachableKeys:
        def get_signing_key_from_jwt(self, token: str) -> PyJWK:
            raise jwt.PyJWKClientConnectionError("JWKS down")

    response = await rename(neon_app(UnreachableKeys()), keys.token())
    assert response.status_code == 503


async def test_routes_reject_missing_and_invalid_tokens(keys: LocalSigningKeys) -> None:
    expired = {"Authorization": f"Bearer {keys.token(seconds=-60)}"}
    transport = ASGITransport(app=neon_app(keys), raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.patch(VIDEO, json=RENAME)
        assert response.status_code == 401
        assert response.headers["WWW-Authenticate"] == "Bearer"
        response = await client.patch(VIDEO, json=RENAME, headers=expired)
        assert response.status_code == 401
        assert response.headers["WWW-Authenticate"] == 'Bearer error="invalid_token"'
        # Admin reads require a token.
        assert (await client.get(VIDEO)).status_code == 401
        # Viewer reads accept anonymous callers but never an invalid token.
        assert (await client.get(CATALOG, headers=expired)).status_code == 401
        assert (await client.get("/ping", headers=expired)).status_code == 200


@pytest.fixture
def database(migrated_database: tuple[str, str]) -> dict[str, Any]:
    url, schema = migrated_database
    return {"database_url": SecretStr(url), "db_schema": schema}


@asynccontextmanager
async def serving(app: FastAPI) -> AsyncGenerator[AsyncClient]:
    async with (
        app.router.lifespan_context(app),
        AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client,
    ):
        yield client


@pytest.mark.integration
async def test_routes_admit_the_callers_the_contract_allows(
    keys: LocalSigningKeys, database: dict[str, Any]
) -> None:
    valid = {"Authorization": f"Bearer {keys.token()}"}
    async with serving(neon_app(keys, **database)) as client:
        # The video is missing, so a 404 shows the request got past authentication.
        assert (await client.patch(VIDEO, json=RENAME, headers=valid)).status_code == 404
        assert (await client.get(VIDEO, headers=valid)).status_code == 404
        assert (await client.get(CATALOG)).status_code == 200


@pytest.mark.integration
async def test_disabled_auth_accepts_any_bearer_token(database: dict[str, Any]) -> None:
    app = create_app(Settings(auth_disabled=True, **database))
    async with serving(app) as client:
        anything = {"Authorization": "Bearer anything"}
        assert (await client.patch(VIDEO, json=RENAME, headers=anything)).status_code == 404
        assert (await client.patch(VIDEO, json=RENAME)).status_code == 401


@pytest.fixture
def auth_environment(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> pytest.MonkeyPatch:
    """Configure the app only through the environment, as a deployed process is."""
    for name in ("AUTH_ISSUER", "AUTH_JWKS_URL", "AUTH_AUDIENCE", "AUTH_DISABLED"):
        monkeypatch.delenv(name, raising=False)
    # Keep a developer's .env out of the test.
    monkeypatch.chdir(tmp_path)
    return monkeypatch


@pytest.mark.parametrize("missing", ["AUTH_ISSUER", "AUTH_JWKS_URL", "AUTH_AUDIENCE"])
def test_missing_auth_configuration_stops_app_construction(
    auth_environment: pytest.MonkeyPatch, missing: str
) -> None:
    for name, value in AUTH_SETTINGS.items():
        if name.upper() != missing:
            auth_environment.setenv(name.upper(), value)
    with pytest.raises(ValueError, match=missing):
        create_app()


def test_disabled_auth_needs_no_neon_configuration(auth_environment: pytest.MonkeyPatch) -> None:
    auth_environment.setenv("AUTH_DISABLED", "true")
    create_app()
