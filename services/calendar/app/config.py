from __future__ import annotations

from functools import lru_cache

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    app_name: str = Field(
        default="maxon-calendar",
        validation_alias=AliasChoices("CALENDAR_APP_NAME", "APP_NAME"),
    )
    app_host: str = Field(
        default="0.0.0.0",
        validation_alias=AliasChoices("CALENDAR_APP_HOST", "APP_HOST"),
    )
    app_port: int = Field(
        default=7132,
        validation_alias=AliasChoices("CALENDAR_APP_PORT", "APP_PORT"),
    )
    database_url: str = Field(
        default="postgresql+asyncpg://maxon:maxon@postgres:5432/maxon",
        validation_alias=AliasChoices("CALENDAR_DATABASE_URL", "DATABASE_URL"),
    )
    public_base_url: str = Field(
        default="http://localhost:7132",
        validation_alias=AliasChoices("CALENDAR_PUBLIC_BASE_URL", "PUBLIC_BASE_URL"),
    )
    ics_past_days: int | None = Field(
        default=30,
        validation_alias=AliasChoices("CALENDAR_ICS_PAST_DAYS", "ICS_PAST_DAYS"),
    )
    ics_future_days: int | None = Field(
        default=365,
        validation_alias=AliasChoices("CALENDAR_ICS_FUTURE_DAYS", "ICS_FUTURE_DAYS"),
    )
    log_level: str = Field(
        default="INFO",
        validation_alias=AliasChoices("CALENDAR_LOG_LEVEL", "LOG_LEVEL"),
    )
    ics_cache_seconds: int = Field(
        default=300,
        validation_alias=AliasChoices("CALENDAR_ICS_CACHE_SECONDS", "ICS_CACHE_SECONDS"),
    )

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    def build_public_ics_url(self, public_token: str) -> str:
        base = self.public_base_url.rstrip("/")
        return f"{base}/calendar/{public_token}.ics"


@lru_cache
def get_settings() -> Settings:
    return Settings()
