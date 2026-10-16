"""Ordered shared-library reads; callers own their transaction."""

from datetime import datetime
from uuid import UUID

from psycopg import AsyncConnection, sql
from psycopg.rows import TupleRow, class_row

from src.domain.library import CursorPosition
from src.domain.videos import VideoRecord


async def list_videos(
    connection: AsyncConnection[TupleRow],
    *,
    administrator: bool,
    status: str | None,
    publication_status: str | None,
    search: str | None,
    limit: int,
    after: CursorPosition | None = None,
) -> list[VideoRecord]:
    clauses = [sql.SQL("TRUE")]
    values: list[str | int | datetime | UUID] = []
    if not administrator:
        clauses.append(sql.SQL("status='READY' AND publication_status='PUBLISHED'"))
    if status is not None:
        clauses.append(sql.SQL("status=%s"))
        values.append(status)
    if publication_status is not None:
        clauses.append(sql.SQL("publication_status=%s"))
        values.append(publication_status)
    if search is not None:
        clauses.append(sql.SQL("strpos(lower(title), lower(%s)) > 0"))
        values.append(search)
    if after is not None:
        clauses.append(sql.SQL("(created_at, id) < (%s, %s)"))
        values.extend((after.created_at, after.id))
    values.append(limit)
    async with connection.cursor(row_factory=class_row(VideoRecord)) as cursor:
        await cursor.execute(
            sql.SQL(
                "SELECT * FROM videos WHERE {} ORDER BY created_at DESC, id DESC LIMIT %s"
            ).format(sql.SQL(" AND ").join(clauses)),
            values,
        )
        return await cursor.fetchall()
