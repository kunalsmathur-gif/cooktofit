from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: Literal["local", "test", "staging", "production"] = "local"
    database_url: str = "postgresql://postgres:postgres@127.0.0.1:54322/postgres"
    db_connect_timeout_s: int = 3


@lru_cache
def get_settings() -> Settings:
    return Settings()
