"""Transport adaptation for shared administrator policy."""

from fastapi import HTTPException, Request

from src.providers.identity import IdentityRejected, IdentityUnavailable
from src.services.authorization import Authorization


async def optional_admin(request: Request) -> bool:
    header = request.headers.get("Authorization")
    if header is None:
        return False
    scheme, _, token = header.partition(" ")
    if scheme.lower() != "bearer" or not token or token != token.strip():
        raise HTTPException(
            401, "A valid bearer token is required.", headers={"WWW-Authenticate": "Bearer"}
        )
    authorization: Authorization = request.app.state.authorization
    try:
        return await authorization.administrator(token)
    except IdentityRejected:
        raise HTTPException(
            401, "A valid bearer token is required.", headers={"WWW-Authenticate": "Bearer"}
        ) from None
    except IdentityUnavailable:
        raise HTTPException(503, "Identity verification is temporarily unavailable.") from None


async def require_admin(request: Request) -> None:
    if request.headers.get("Authorization") is None:
        raise HTTPException(
            401, "A bearer token is required.", headers={"WWW-Authenticate": "Bearer"}
        )
    if not await optional_admin(request):
        raise HTTPException(403, "Administrator access is required.")
