from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central app configuration. Everything environment-specific lives here —
    never hardcode league rules, credentials, or provider toggles elsewhere."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://fantamazor:fantamazor@localhost:5432/fantamazor"
    redis_url: str = "redis://localhost:6379/0"
    session_secret_key: str = "change-me-to-a-random-secret"

    admin_username: str = "admin"
    admin_password: str = "change-me"

    # demo | manual | live — see providers/registry.py
    data_provider_mode: str = "demo"

    api_football_api_key: str | None = None
    api_football_base_url: str = "https://v3.football.api-sports.io"

    frontend_origin: str = "http://localhost:3000"


@lru_cache
def get_settings() -> Settings:
    return Settings()
