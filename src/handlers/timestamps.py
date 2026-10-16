"""Canonical UTC formatting at the HTTP boundary."""

from datetime import UTC, datetime


def utc_timestamp(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")
