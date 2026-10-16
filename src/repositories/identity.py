"""Read current roles from the provider-owned Managed Better Auth schema."""

from psycopg import sql

from src.repositories.database import Database


class NeonRoles:
    def __init__(self, database: Database, schema: str) -> None:
        self.database = database
        self.schema = schema

    async def is_administrator(self, subject: str) -> bool:
        async with self.database.connection() as connection:
            cursor = await connection.execute(
                sql.SQL('SELECT role FROM {}."user" WHERE id = %s').format(
                    sql.Identifier(self.schema)
                ),
                (subject,),
            )
            row = await cursor.fetchone()
            return (
                row is not None
                and isinstance(row[0], str)
                and "admin" in {role.strip() for role in row[0].split(",")}
            )
