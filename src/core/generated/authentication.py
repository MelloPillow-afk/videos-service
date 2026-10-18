# fmt: off
"""Bearer authentication for operations whose contract declares `security`.

The service supplies the verifier as `app.state.authenticator` before calling
`register_routers(app)`. Verified identities are available as `request.auth`.
"""

from dataclasses import dataclass
from inspect import iscoroutinefunction
from typing import Protocol

from fastapi import FastAPI, HTTPException, Request


@dataclass(frozen=True, slots=True)
class Authentication:
    sub: str


class AuthenticationRejected(Exception):
    """The token is malformed, expired, or not issued for this service."""


class AuthenticationUnavailable(Exception):
    """The identity provider cannot verify tokens right now."""


class Authenticator(Protocol):
    async def verify(self, token: str) -> str:
        """Return the token subject or raise an Authentication* error."""
        ...


def require_authenticator(app: FastAPI) -> None:
    authenticator = getattr(app.state, "authenticator", None)
    if not iscoroutinefunction(getattr(authenticator, "verify", None)):
        raise RuntimeError(
            "contract operations require bearer authentication; set "
            "app.state.authenticator to an object with `async verify(token) -> str` "
            "before register_routers(app)"
        )


def _challenge(detail: str, error: str | None = None) -> HTTPException:
    value = "Bearer" if error is None else f'Bearer error="{error}"'
    return HTTPException(401, detail, headers={"WWW-Authenticate": value})


def _token(request: Request) -> str | None:
    header = request.headers.get("Authorization")
    if header is None:
        return None
    scheme, _, token = header.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise _challenge("Bearer token required.")
    return token.strip()


async def _authenticate(request: Request, token: str) -> Authentication:
    authenticator: Authenticator = request.app.state.authenticator
    try:
        sub = await authenticator.verify(token)
    except AuthenticationRejected:
        raise _challenge("Invalid bearer token.", "invalid_token") from None
    except AuthenticationUnavailable:
        raise HTTPException(503, "Authentication is unavailable.") from None
    return Authentication(sub=sub)


async def require_authentication(request: Request) -> None:
    token = _token(request)
    if token is None:
        raise _challenge("Authentication required.")
    request.scope["auth"] = await _authenticate(request, token)


async def optional_authentication(request: Request) -> None:
    token = _token(request)
    request.scope["auth"] = None if token is None else await _authenticate(request, token)
