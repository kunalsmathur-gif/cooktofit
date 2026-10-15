from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app import db
from app.config import Settings, get_settings
from app.main import app


@pytest.fixture
def client() -> Iterator[TestClient]:
    app.dependency_overrides[get_settings] = lambda: Settings(environment="test")
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_healthz_is_ok_without_dependencies(client: TestClient) -> None:
    res = client.get("/healthz")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}


def test_readyz_ok_when_database_reachable(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def ok(_: Settings) -> None:
        return None

    monkeypatch.setattr(db, "ping", ok)
    res = client.get("/readyz")
    assert res.status_code == 200
    assert res.json() == {"status": "ok", "database": "up"}


def test_readyz_503_when_database_down(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    async def down(_: Settings) -> None:
        raise OSError("connection refused")

    monkeypatch.setattr(db, "ping", down)
    res = client.get("/readyz")
    assert res.status_code == 503
    assert res.json() == {"status": "unavailable", "database": "down"}
