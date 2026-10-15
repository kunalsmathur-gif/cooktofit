import psycopg

from app.config import Settings


async def ping(settings: Settings) -> None:
    """Raise if Postgres is unreachable."""
    async with await psycopg.AsyncConnection.connect(
        settings.database_url, connect_timeout=settings.db_connect_timeout_s
    ) as conn:
        await conn.execute("select 1")
