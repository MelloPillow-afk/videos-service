"""Generated activation preserves custom selection and the video lifecycle."""

from psycopg import AsyncConnection
from psycopg.rows import TupleRow

from src.repositories.workers import Work, eligible, history


async def complete(connection: AsyncConnection[TupleRow], work: Work, key: str) -> bool:
    if not await eligible(connection, work):
        return False
    # Never write custom_thumbnail_key or the video lifecycle/source validity.
    await connection.execute(
        """UPDATE videos SET generated_thumbnail_status='READY',
        generated_thumbnail_key=%s,updated_at=now() WHERE id=%s""",
        (key, work.video_id),
    )
    await connection.execute(
        "UPDATE jobs SET state='SUCCEEDED',updated_at=now() WHERE id=%s", (work.id,)
    )
    await history(connection, work, "SUCCEEDED")
    return True
