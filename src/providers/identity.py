"""Cryptographic Neon Auth identity verification, independent of role authorization."""

import asyncio
from typing import Protocol

import jwt
from jwt import PyJWK, PyJWKClient

from src.config import Settings


class SigningKeys(Protocol):
    def get_signing_key_from_jwt(self, token: str) -> PyJWK: ...


class IdentityRejected(Exception):
    pass


class IdentityUnavailable(Exception):
    pass


class NeonIdentity:
    def __init__(self, settings: Settings, signing_keys: SigningKeys | None = None) -> None:
        self.settings = settings
        self.keys = signing_keys or (
            PyJWKClient(settings.auth_jwks_url, timeout=5, lifespan=300)
            if settings.auth_jwks_url
            else None
        )

    async def verify(self, token: str) -> str:
        if self.keys is None or not self.settings.auth_issuer:
            raise IdentityUnavailable
        try:
            key = await asyncio.to_thread(self.keys.get_signing_key_from_jwt, token)
            payload = jwt.decode(
                token,
                key.key,
                algorithms=["EdDSA"],
                issuer=self.settings.auth_issuer,
                audience=self.settings.auth_audience,
                options={
                    "require": ["exp", "iat", "sub", "iss"],
                    "verify_aud": self.settings.auth_audience is not None,
                },
            )
            subject = payload["sub"]
            if not isinstance(subject, str) or not subject:
                raise IdentityRejected
            return subject
        except jwt.PyJWKClientConnectionError:
            raise IdentityUnavailable from None
        except (jwt.PyJWTError, ValueError, TypeError, KeyError):
            raise IdentityRejected from None
