"""Database-independent process reachability."""

from src.schemas.generated.health import Ping


async def ping() -> Ping:
    return Ping(status="ok")
