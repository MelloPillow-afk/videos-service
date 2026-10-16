"""Identity plus current-role policy; JWT role claims are never authority."""

from psycopg import Error
from psycopg_pool import PoolTimeout

from src.providers.identity import IdentityUnavailable, NeonIdentity
from src.repositories.identity import NeonRoles


class Authorization:
    def __init__(self, identity: NeonIdentity, roles: NeonRoles) -> None:
        self.identity = identity
        self.roles = roles

    async def administrator(self, token: str) -> bool:
        subject = await self.identity.verify(token)
        try:
            return await self.roles.is_administrator(subject)
        except (Error, PoolTimeout):
            raise IdentityUnavailable from None
