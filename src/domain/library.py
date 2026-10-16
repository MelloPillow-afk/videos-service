"""Validated continuation positions and immutable query context."""

from base64 import b64decode, urlsafe_b64encode
from binascii import Error as Base64Error
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from json import dumps
from typing import Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, ValidationError


class InvalidCursor(Exception):
    pass


class CursorPosition(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: Literal[1] = 1
    context: str
    created_at: AwareDatetime
    id: UUID


@dataclass(frozen=True)
class LibraryQuery:
    administrator: bool
    status: str | None
    publication_status: str | None
    search: str | None
    limit: int

    def fingerprint(self) -> str:
        context = dumps(
            {
                "administrator": self.administrator,
                "status": self.status,
                "publication_status": self.publication_status,
                "search": self.search,
                "limit": self.limit,
            },
            sort_keys=True,
        )
        return sha256(context.encode()).hexdigest()

    def position(self, token: str | None) -> CursorPosition | None:
        if token is None:
            return None
        try:
            if len(token) > 2048:
                raise InvalidCursor
            payload = b64decode(token + "=" * (-len(token) % 4), altchars=b"-_", validate=True)
            position = CursorPosition.model_validate_json(payload)
            if position.context != self.fingerprint():
                raise InvalidCursor
            return position
        except (Base64Error, ValidationError, ValueError):
            raise InvalidCursor from None

    def continuation(self, created_at: datetime, id: UUID) -> str:
        payload = CursorPosition(context=self.fingerprint(), created_at=created_at, id=id)
        return urlsafe_b64encode(payload.model_dump_json().encode()).decode().rstrip("=")
