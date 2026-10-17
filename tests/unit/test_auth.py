"""Neon Auth verification, fail-fast configuration, and bearer enforcement over HTTP."""

from pathlib import Path
from typing import Any

import jwt
import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient, Response
from jwt import PyJWK

from src.app import create_app
from src.config import Settings
from src.providers.auth import SigningKeys
from tests.auth_provider import AUTH_SETTINGS, LocalSigningKeys

VIDEO = "/v1/admin/videos/550e8400-e29b-41d4-a716-446655440000"
CATALOG = "/v1/videos"
RENAME = {"title": "Renamed"}


@pytest.fixture
def keys() -> LocalSigningKeys:
    return LocalSigningKeys()


def neon_app(keys: SigningKeys) -> FastAPI:
    return create_app(Settings(db_pool_min_size=0, **AUTH_SETTINGS), signing_keys=keys)


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


async def test_routes_enforce_contract_security(keys: LocalSigningKeys) -> None:
    app = neon_app(keys)
    valid = {"Authorization": f"Bearer {keys.token()}"}
    expired = {"Authorization": f"Bearer {keys.token(seconds=-60)}"}
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.patch(VIDEO, json=RENAME)
        assert response.status_code == 401
        assert response.headers["WWW-Authenticate"] == "Bearer"
        response = await client.patch(VIDEO, json=RENAME, headers=expired)
        assert response.status_code == 401
        assert response.headers["WWW-Authenticate"] == 'Bearer error="invalid_token"'
        # Accepted requests pass authentication; without a database they may fail afterwards.
        assert (await client.patch(VIDEO, json=RENAME, headers=valid)).status_code != 401
        # Admin reads require a token.
        assert (await client.get(VIDEO)).status_code == 401
        assert (await client.get(VIDEO, headers=valid)).status_code != 401
        # Viewer reads accept anonymous callers but never an invalid token.
        assert (await client.get(CATALOG)).status_code == 200
        assert (await client.get(CATALOG, headers=expired)).status_code == 401
        assert (await client.get("/ping", headers=expired)).status_code == 200


async def test_disabled_auth_accepts_any_bearer_token() -> None:
    app = create_app(Settings(db_pool_min_size=0, auth_disabled=True))
    assert (await rename(app, "anything")).status_code != 401
    assert (await rename(app, None)).status_code == 401


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
