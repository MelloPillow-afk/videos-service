"""Bearer token verifiers for the generated authentication dependency."""

import asyncio
from typing import Protocol

import jwt
from jwt import PyJWK, PyJWKClient

from src.config import Settings
from src.core.generated.authentication import AuthenticationRejected, AuthenticationUnavailable


class SigningKeys(Protocol):
    def get_signing_key_from_jwt(self, token: str) -> PyJWK: ...


class NeonIdentity:
    """Verify Neon Auth JWTs locally against its cached JWKS."""

    def __init__(self, settings: Settings, signing_keys: SigningKeys | None = None) -> None:
        if not (settings.auth_issuer and settings.auth_jwks_url and settings.auth_audience):
            # Settings rejects missing values first; this check only narrows their types.
            raise ValueError("Neon Auth settings are incomplete")  # pragma: no cover
        self.issuer = settings.auth_issuer
        self.audience = settings.auth_audience
        self.keys = signing_keys or PyJWKClient(settings.auth_jwks_url, timeout=5, lifespan=300)

    async def verify(self, token: str) -> str:
        try:
            key = await asyncio.to_thread(self.keys.get_signing_key_from_jwt, token)
            payload = jwt.decode(
                token,
                key.key,
                algorithms=["EdDSA"],
                issuer=self.issuer,
                audience=self.audience,
                options={"require": ["exp", "iat", "sub", "iss", "aud"]},
            )
        except jwt.PyJWKClientConnectionError:
            raise AuthenticationUnavailable from None
        except (jwt.PyJWTError, ValueError, TypeError, KeyError):
            raise AuthenticationRejected from None
        subject = payload["sub"]
        if not isinstance(subject, str) or not subject:
            raise AuthenticationRejected
        return subject


class DisabledAuth:
    """Local development stand-in: any bearer token authenticates as one subject."""

    def __init__(self, subject: str) -> None:
        self.subject = subject

    async def verify(self, token: str) -> str:
        return self.subject
