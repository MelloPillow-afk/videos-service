"""Controlled external identity signing keys; real JWT cryptography remains enabled."""

from datetime import UTC, datetime, timedelta

import jwt
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from jwt import PyJWK
from jwt.algorithms import OKPAlgorithm

ISSUER = "https://auth.test"
SUBJECT = "administrator-1"


class LocalSigningKeys:
    def __init__(self) -> None:
        self.private_key = Ed25519PrivateKey.generate()
        self.public_key = PyJWK.from_dict(
            OKPAlgorithm.to_jwk(self.private_key.public_key(), as_dict=True)
            | {"kid": "test-key", "use": "sig", "alg": "EdDSA"}
        )

    def get_signing_key_from_jwt(self, token: str) -> PyJWK:
        if jwt.get_unverified_header(token).get("kid") != "test-key":
            raise jwt.InvalidTokenError("Unknown key")
        return self.public_key

    def token(
        self,
        *,
        subject: str = SUBJECT,
        issuer: str = ISSUER,
        seconds: int = 900,
        audience: str = ISSUER,
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
            headers={"kid": "test-key"},
        )
