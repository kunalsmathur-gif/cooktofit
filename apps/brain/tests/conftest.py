import os
from collections.abc import AsyncIterator
from typing import Any

import psycopg
import pytest

from app.config import Settings


@pytest.fixture
async def conn() -> AsyncIterator[psycopg.AsyncConnection[Any]]:
    """A connection whose every change is rolled back. Skips without a DB unless REQUIRE_DB=1."""
    try:
        c = await psycopg.AsyncConnection.connect(
            Settings().database_url, autocommit=True, connect_timeout=2
        )
    except psycopg.OperationalError:
        if os.environ.get("REQUIRE_DB") == "1":
            raise
        pytest.skip("database not reachable (run `make db-start`)")
    async with c:
        async with c.transaction(force_rollback=True):
            yield c
