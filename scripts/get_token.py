"""Sign in to Neon Auth with email and password and print a bearer token for this service.

The token goes to stdout so it can be captured; diagnostics go to stderr:

    TOKEN=$(uv run --locked python scripts/get_token.py --email you@example.com)
    curl -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8000/v1/videos

The password is read from NEON_AUTH_PASSWORD or prompted for; it is never stored.
Neon Auth tokens last 15 minutes. With AUTH_DISABLED=true the service accepts any
bearer token, so this script is only needed against real Neon Auth.
"""

import argparse
import getpass
import os
import sys
from datetime import UTC, datetime
from typing import Any

import httpx
import jwt
from pydantic_settings import BaseSettings, SettingsConfigDict

JWKS_SUFFIX = "/.well-known/jwks.json"


class AuthSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    auth_issuer: str | None = None
    auth_jwks_url: str | None = None
    auth_audience: str | None = None
    neon_auth_email: str | None = None


def fail(message: str) -> None:
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(1)


def describe(response: httpx.Response) -> str:
    return f"HTTP {response.status_code} from {response.request.url}: {response.text[:300]}"


def fetch_token(auth_url: str, email: str, password: str, origin: str) -> str:
    # Better Auth checks Origin against the project's trusted domains.
    with httpx.Client(base_url=auth_url, headers={"Origin": origin}, timeout=10) as client:
        response = client.post("/sign-in/email", json={"email": email, "password": password})
        if response.status_code != 200:
            fail(f"sign-in failed: {describe(response)}")
        # The session cookie set by sign-in authenticates the token request.
        response = client.get("/token")
        if response.status_code != 200:
            fail(f"token request failed: {describe(response)}")
        token = response.json().get("token")
        if not isinstance(token, str) or not token:
            fail(f"token response has no token: {describe(response)}")
        return token


def report(token: str, settings: AuthSettings) -> None:
    claims: dict[str, Any] = jwt.decode(token, options={"verify_signature": False})
    expires = datetime.fromtimestamp(claims["exp"], UTC) if "exp" in claims else None
    print(f"sub: {claims.get('sub')}", file=sys.stderr)
    print(f"iss: {claims.get('iss')}", file=sys.stderr)
    print(f"aud: {claims.get('aud')}", file=sys.stderr)
    print(f"expires: {expires.isoformat() if expires else 'unknown'}", file=sys.stderr)
    aud: Any = claims.get("aud")
    audiences: list[Any] = aud if isinstance(aud, list) else [aud]  # pyright: ignore[reportUnknownVariableType]
    if settings.auth_issuer and claims.get("iss") != settings.auth_issuer:
        print(f"warning: iss differs from AUTH_ISSUER={settings.auth_issuer}", file=sys.stderr)
    if settings.auth_audience and settings.auth_audience not in audiences:
        print(f"warning: aud lacks AUTH_AUDIENCE={settings.auth_audience}", file=sys.stderr)


def main() -> None:
    settings = AuthSettings()
    default_url = (
        settings.auth_jwks_url.removesuffix(JWKS_SUFFIX)
        if settings.auth_jwks_url and settings.auth_jwks_url.endswith(JWKS_SUFFIX)
        else None
    )
    parser = argparse.ArgumentParser(description="Print a Neon Auth bearer token.")
    parser.add_argument(
        "--auth-url",
        default=default_url,
        help="Neon Auth URL including its path (default: AUTH_JWKS_URL without the JWKS suffix)",
    )
    parser.add_argument(
        "--email", default=settings.neon_auth_email, help="default: NEON_AUTH_EMAIL"
    )
    parser.add_argument(
        "--origin",
        default="http://localhost:3000",
        help="Origin header; must be a trusted domain in Neon Auth (default: %(default)s)",
    )
    arguments = parser.parse_args()
    if not arguments.auth_url:
        fail("pass --auth-url or set AUTH_JWKS_URL")
    if not arguments.email:
        fail("pass --email or set NEON_AUTH_EMAIL")
    password = os.environ.get("NEON_AUTH_PASSWORD") or getpass.getpass(
        f"Password for {arguments.email}: "
    )
    token = fetch_token(arguments.auth_url.rstrip("/"), arguments.email, password, arguments.origin)
    report(token, settings)
    print(token)


if __name__ == "__main__":
    main()
