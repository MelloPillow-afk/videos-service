"""Visibility and shared-library discovery."""

from src.domain.library import LibraryQuery
from src.domain.videos import VideoRecord
from src.repositories.database import Database
from src.repositories.library import list_videos


class LibraryService:
    def __init__(self, database: Database) -> None:
        self.database = database

    async def list(
        self,
        *,
        query: LibraryQuery,
        cursor: str | None,
    ) -> tuple[list[VideoRecord], str | None]:
        after = query.position(cursor)
        async with self.database.connection() as connection:
            videos = await list_videos(
                connection,
                administrator=query.administrator,
                status=query.status,
                publication_status=query.publication_status,
                search=query.search,
                limit=query.limit + 1,
                after=after,
            )
        page = videos[: query.limit]
        token = (
            query.continuation(page[-1].created_at, page[-1].id)
            if len(videos) > query.limit
            else None
        )
        return page, token
