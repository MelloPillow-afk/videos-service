"""Insert application rows directly when a test needs existing state."""

from uuid import uuid4

from psycopg import AsyncConnection


async def insert_video(db: AsyncConnection, **values: object) -> str:
    video_id = str(values.pop("id", uuid4()))
    values.setdefault("title", "Introduction to Faith")
    columns = ", ".join(["id", *values])
    placeholders = ", ".join(["%s"] * (len(values) + 1))
    # Column names come from test code, not user input.
    await db.execute(
        f"INSERT INTO videos ({columns}) VALUES ({placeholders})",
        (video_id, *values.values()),
    )
    return video_id
