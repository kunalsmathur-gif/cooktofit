from typing import Any

import psycopg
from psycopg_pool import AsyncConnectionPool

from app.config import Settings


async def ping(settings: Settings) -> None:
    """Raise if Postgres is unreachable."""
    async with await psycopg.AsyncConnection.connect(
        settings.database_url, connect_timeout=settings.db_connect_timeout_s
    ) as conn:
        await conn.execute("select 1")


def make_pool(settings: Settings) -> AsyncConnectionPool[psycopg.AsyncConnection[Any]]:
    # autocommit so each `conn.transaction()` block is a real transaction.
    return AsyncConnectionPool(
        settings.database_url,
        open=False,
        min_size=1,
        max_size=5,
        kwargs={"autocommit": True, "connect_timeout": settings.db_connect_timeout_s},
    )
