# fmt: off
"""Generated wire-schema helpers: validation preserves original JSON strings."""

import re
from datetime import datetime
from typing import Any, cast
from urllib.parse import urlsplit
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class WireModel(BaseModel):
    model_config = ConfigDict(extra="allow")


def omitted() -> Any:
    """Unvalidated absence default; supplied null still fails the field type."""
    return None


def validate_allowed_values[T](value: T, allowed: list[object]) -> T:
    """Apply enum/const semantics after native scalar parsing."""
    if value not in allowed:
        raise ValueError(f"expected one of {allowed!r}")
    return value


def require_properties(value: object, alternatives: list[list[str]]) -> object:
    """Presence depends on supplied wire keys, independently of their values."""
    if isinstance(value, dict):
        supplied = cast(dict[str, Any], value)
        if not any(all(field in supplied for field in group) for group in alternatives):
            raise ValueError("at least one recognized update field is required")
        return supplied
    return value


def validate_format(value: str, format_name: str) -> str:
    if format_name == "uuid":
        if (
            re.fullmatch(
                r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}",
                value,
            )
            is None
        ):
            raise ValueError("invalid UUID")
        UUID(value)
    elif format_name == "date-time":
        if (
            re.fullmatch(
                r"\d{4}-\d{2}-\d{2}[Tt]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:[Zz]|[+-]\d{2}:\d{2})",
                value,
            )
            is None
        ):
            raise ValueError("expected RFC3339 date-time")
        datetime.fromisoformat(value.replace("t", "T").replace("z", "Z"))
    elif format_name in {"uri", "uri-reference"}:
        if any(c.isspace() or ord(c) < 32 for c in value) or re.search(
            r"%(?![0-9a-fA-F]{2})", value
        ):
            raise ValueError("invalid URI characters")
        parsed = urlsplit(value)
        if format_name == "uri" and not parsed.scheme:
            raise ValueError("expected absolute URI")
        if parsed.scheme.lower() in {"http", "https"} and not parsed.hostname:
            raise ValueError("HTTP URI must contain a host")
        _ = parsed.port
    return value
