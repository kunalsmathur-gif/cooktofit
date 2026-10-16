from fastapi.testclient import TestClient

from app.config import Settings, get_settings
from app.main import app


def test_simulator_hidden_outside_dev() -> None:
    app.dependency_overrides[get_settings] = lambda: Settings(
        environment="production", phone_hash_key="real-secret"
    )
    try:
        with TestClient(app) as client:
            res = client.post("/dev/simulate", json={"from_phone": "+919800000001", "text": "hi"})
        assert res.status_code == 404
    finally:
        app.dependency_overrides.clear()


def test_production_requires_real_phone_hash_key() -> None:
    import pytest

    with pytest.raises(ValueError, match="PHONE_HASH_KEY"):
        Settings(environment="production")
