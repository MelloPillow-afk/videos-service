"""Controlled Neon Auth signing keys; real JWT cryptography remains enabled."""

from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from jwt import PyJWK
from jwt.algorithms import OKPAlgorithm

ISSUER = "https://auth.test"
SUBJECT = "user-1"
AUTH_SETTINGS: dict[str, Any] = {
    "auth_issuer": ISSUER,
    "auth_audience": ISSUER,
    "auth_jwks_url": f"{ISSUER}/.well-known/jwks.json",
}


class LocalSigningKeys:
    def __init__(self) -> None:
        self.private_key = Ed25519PrivateKey.generate()
        self.public_key = PyJWK.from_dict(
            OKPAlgorithm.to_jwk(self.private_key.public_key(), as_dict=True)
            | {"kid": "test-key", "use": "sig", "alg": "EdDSA"}
        )

    def get_signing_key_from_jwt(self, token: str) -> PyJWK:
        if jwt.get_unverified_header(token).get("kid") != "test-key":
            raise jwt.PyJWKClientError("Unknown key")
        return self.public_key

    def token(
        self,
        *,
        subject: object = SUBJECT,
        issuer: str = ISSUER,
        audience: str = ISSUER,
        seconds: int = 900,
        kid: str = "test-key",
    ) -> str:
        now = datetime.now(UTC)
        return jwt.encode(
            {
                "sub": subject,
                "iss": issuer,
                "aud": audience,
                "iat": now,
                "exp": now + timedelta(seconds=seconds),
            },
            self.private_key,
            algorithm="EdDSA",
            headers={"kid": kid},
        )
