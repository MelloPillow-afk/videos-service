"""Neon Auth verification, fail-fast configuration, and bearer enforcement over HTTP."""

from pathlib import Path
from typing import Any

import jwt
import pytest
from httpx import ASGITransport, AsyncClient
from jwt import PyJWK
from pydantic import ValidationError

from src.app import create_app
from src.config import Settings
from src.core.generated.authentication import AuthenticationRejected, AuthenticationUnavailable
from src.providers.auth import DisabledAuth, NeonIdentity
from tests.auth_provider import AUTH_SETTINGS, SUBJECT, LocalSigningKeys

VIDEO = "/v1/videos/550e8400-e29b-41d4-a716-446655440000"


@pytest.fixture
def keys() -> LocalSigningKeys:
    return LocalSigningKeys()


@pytest.fixture
def identity(keys: LocalSigningKeys) -> NeonIdentity:
    return NeonIdentity(Settings(**AUTH_SETTINGS), keys)


async def test_valid_token_returns_subject(identity: NeonIdentity, keys: LocalSigningKeys) -> None:
    assert await identity.verify(keys.token()) == SUBJECT


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
    identity: NeonIdentity, keys: LocalSigningKeys, claims: dict[str, Any]
) -> None:
    with pytest.raises(AuthenticationRejected):
        await identity.verify(keys.token(**claims))


async def test_tokens_from_other_keys_are_rejected(identity: NeonIdentity) -> None:
    for token in ("not-a-jwt", LocalSigningKeys().token()):
        with pytest.raises(AuthenticationRejected):
            await identity.verify(token)


async def test_unreachable_jwks_is_unavailable(keys: LocalSigningKeys) -> None:
    class UnreachableKeys:
        def get_signing_key_from_jwt(self, token: str) -> PyJWK:
            raise jwt.PyJWKClientConnectionError("JWKS down")

    identity = NeonIdentity(Settings(**AUTH_SETTINGS), UnreachableKeys())
    with pytest.raises(AuthenticationUnavailable):
        await identity.verify(keys.token())


@pytest.mark.parametrize("missing", ["auth_issuer", "auth_jwks_url", "auth_audience"])
def test_settings_require_neon_auth_unless_disabled(missing: str) -> None:
    settings: dict[str, Any] = {**AUTH_SETTINGS, missing: None}
    with pytest.raises(ValidationError, match="AUTH_DISABLED"):
        Settings(**settings)
    assert Settings(auth_disabled=True).auth_disabled_subject == "dev-user"


async def test_disabled_auth_accepts_any_token_as_configured_subject() -> None:
    assert await DisabledAuth("dev-user").verify("anything") == "dev-user"


async def test_routes_enforce_contract_security(keys: LocalSigningKeys) -> None:
    app = create_app(Settings(db_pool_min_size=0, **AUTH_SETTINGS), signing_keys=keys)
    valid = {"Authorization": f"Bearer {keys.token()}"}
    expired = {"Authorization": f"Bearer {keys.token(seconds=-60)}"}
    rename = {"title": "Renamed"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.patch(VIDEO, json=rename)
        assert response.status_code == 401
        assert response.headers["WWW-Authenticate"] == "Bearer"
        response = await client.patch(VIDEO, json=rename, headers=expired)
        assert response.status_code == 401
        assert response.headers["WWW-Authenticate"] == 'Bearer error="invalid_token"'
        assert (await client.patch(VIDEO, json=rename, headers=valid)).status_code == 200
        # Viewer reads accept anonymous callers but never an invalid token.
        assert (await client.get(VIDEO)).status_code == 200
        assert (await client.get(VIDEO, headers=valid)).status_code == 200
        assert (await client.get(VIDEO, headers=expired)).status_code == 401
        assert (await client.get("/ping", headers=expired)).status_code == 200


def test_missing_auth_configuration_stops_app_construction(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    for name in ("AUTH_ISSUER", "AUTH_JWKS_URL", "AUTH_AUDIENCE", "AUTH_DISABLED"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.chdir(tmp_path)
    with pytest.raises(ValidationError, match="AUTH_ISSUER"):
        create_app(Settings())
