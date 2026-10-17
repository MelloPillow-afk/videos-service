"""Wire formats shared by handlers: UTC timestamps, list page tokens, and thumbnails."""

import base64
import json
from collections.abc import Callable
from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException

from src.clients import cloudflare
from src.domain.jobs import JobStatus
from src.domain.videos import Video
from src.schemas.generated.shared import Pagination
from src.schemas.generated.thumbnails import ThumbnailImage, ThumbnailStatus

type Position = tuple[datetime, UUID]


def timestamp(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def thumbnail(video: Video) -> ThumbnailImage:
    """The generated thumbnail once ready, with its generation job's progress."""
    key = video.generated_thumbnail_key
    return ThumbnailImage(
        status=_THUMBNAIL_STATUS[video.thumbnail_job_status],
        source="GENERATED" if key else "NONE",
        url=cloudflare.media_url(key) if key else None,
    )


# Until generation is queued, or while it runs, the thumbnail is pending.
_THUMBNAIL_STATUS: dict[JobStatus | None, ThumbnailStatus] = {
    None: "PENDING",
    JobStatus.QUEUED: "PENDING",
    JobStatus.RUNNING: "PENDING",
    JobStatus.SUCCEEDED: "READY",
    JobStatus.FAILED: "FAILED",
}


def page_position(page_token: str | None) -> Position | None:
    """The (sort timestamp, id) a list resumes after, from a token that page returned."""
    if page_token is None:
        return None
    try:
        padded = page_token + "=" * (-len(page_token) % 4)
        fields = json.loads(base64.urlsafe_b64decode(padded))
        at = datetime.fromisoformat(fields["t"])
        if at.tzinfo is None:
            raise ValueError(at)
        return at, UUID(fields["id"])
    except (ValueError, TypeError, KeyError):
        raise HTTPException(status_code=400, detail="The page token is invalid.") from None


def page[T](
    rows: list[T], limit: int, position: Callable[[T], Position]
) -> tuple[list[T], Pagination]:
    """Split rows fetched with limit + 1 into one page and where the next one starts."""
    rows, has_more = rows[:limit], len(rows) > limit
    next_page_token = _page_token(*position(rows[-1])) if has_more else None
    return rows, Pagination(next_page_token=next_page_token, has_more=has_more)


def _page_token(at: datetime, id_: UUID) -> str:
    # Full microseconds: a truncated timestamp would skip or repeat rows that share it.
    fields = {"t": at.isoformat(timespec="microseconds"), "id": str(id_)}
    encoded = base64.urlsafe_b64encode(json.dumps(fields, separators=(",", ":")).encode())
    return encoded.decode().rstrip("=")
