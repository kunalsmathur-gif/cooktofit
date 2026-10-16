from functools import lru_cache
from typing import Literal

from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEV_PHONE_HASH_KEY = "local-dev-only-not-a-secret"  # noqa: S105


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: Literal["local", "test", "staging", "production"] = "local"
    database_url: str = "postgresql://postgres:postgres@127.0.0.1:54322/postgres"
    db_connect_timeout_s: int = 3

    # HMAC key for hashing phone numbers in gate logs. Phone numbers are a small,
    # enumerable space, so a plain hash would be reversible.
    phone_hash_key: SecretStr = SecretStr(DEV_PHONE_HASH_KEY)
    # Our WhatsApp business number (digits only), used to build private invite links.
    whatsapp_number: str | None = None
    invite_ttl_days: int = 7

    @property
    def is_dev(self) -> bool:
        return self.environment in ("local", "test")

    @model_validator(mode="after")
    def _require_real_secrets_outside_dev(self) -> "Settings":
        if not self.is_dev and self.phone_hash_key.get_secret_value() == DEV_PHONE_HASH_KEY:
            raise ValueError("PHONE_HASH_KEY must be set outside local/test")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
