from __future__ import annotations

import os
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_secret_key: str = "dev-only-change-me-in-production"
    debug: bool = True
    cors_allowed_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    inventory_db_host: str = "localhost"
    inventory_db_port: int = 5433
    inventory_db_name: str = "db_inventory"
    inventory_db_user: str = "postgres"
    inventory_db_password: str = "postgres"

    jwt_access_lifetime_hours: int = 12
    jwt_refresh_lifetime_days: int = 7

    powersync_url: str = "http://localhost:2000"
    powersync_jwt_secret: str = "inventory-dev-powersync-secret-key-32b"
    powersync_jwt_audience: str = "http://localhost:2000"
    powersync_jwt_kid: str = "inventory-local-key"

    google_api_key: str = ""
    openai_api_key: str = ""
    deepseek_api_key: str = ""
    openrouter_api_key: str = ""
    inventory_agent_model: str = ""

    @property
    def database_url(self) -> str:
        return (
            f"postgresql://{self.inventory_db_user}:{self.inventory_db_password}"
            f"@{self.inventory_db_host}:{self.inventory_db_port}/{self.inventory_db_name}"
        )

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.cors_allowed_origins.split(",") if o.strip()]

    @property
    def resolved_agent_model(self) -> str:
        if self.inventory_agent_model:
            return self.inventory_agent_model
        if self.openrouter_api_key or (
            self.openai_api_key.startswith("sk-or-") and self.openai_api_key
        ):
            return "openrouter:openai/gpt-4o"
        if self.google_api_key:
            return "google:gemini-2.5-flash-lite"
        if self.deepseek_api_key:
            return "deepseek:deepseek-v4-flash"
        return "openai:gpt-4o"


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    if not settings.openrouter_api_key and settings.openai_api_key.startswith("sk-or-"):
        object.__setattr__(settings, "openrouter_api_key", settings.openai_api_key)
        os.environ.setdefault("OPENROUTER_API_KEY", settings.openai_api_key)
    for key, val in (
        ("GOOGLE_API_KEY", settings.google_api_key),
        ("OPENAI_API_KEY", settings.openai_api_key),
        ("DEEPSEEK_API_KEY", settings.deepseek_api_key),
        ("OPENROUTER_API_KEY", settings.openrouter_api_key),
    ):
        if val:
            os.environ.setdefault(key, val)
    return settings
