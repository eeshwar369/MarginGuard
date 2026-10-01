import os
from functools import lru_cache
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="MG_", env_file=".env", extra="ignore", hide_input_in_errors=True
    )
    env: str = "development"
    data_dir: Path = Path("data")
    static_dir: Path = Path("web/out")
    app_origin: str = Field(
        default_factory=lambda: os.getenv("RENDER_EXTERNAL_URL") or "http://localhost:3000"
    )
    database_url: SecretStr = SecretStr("")
    cookie_secure: bool = False
    allow_registration: bool = True
    allow_demo: bool = True
    max_upload_mb: int = Field(8, ge=1, le=50)
    max_rows: int = Field(50000, ge=100, le=200000)
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.8-flash"
    ai_timeout_seconds: int = Field(35, ge=5, le=90)

    @model_validator(mode="after")
    def production_config(self):
        database_url = self.database_url.get_secret_value()
        if database_url:
            parsed = urlsplit(database_url)
            if parsed.scheme not in {"postgres", "postgresql"} or not parsed.hostname:
                raise ValueError("MG_DATABASE_URL must be a PostgreSQL connection URL")
            if self.env == "production" and parse_qs(parsed.query).get("sslmode", [""])[0] not in {
                "require",
                "verify-ca",
                "verify-full",
            }:
                raise ValueError("Production MG_DATABASE_URL requires sslmode=require or stricter")
        if os.getenv("RENDER") == "true" and not database_url:
            raise ValueError("Render requires MG_DATABASE_URL so data survives service restarts")
        if self.env == "production" and (
            not self.cookie_secure or not self.app_origin.startswith("https://")
        ):
            raise ValueError("Production requires MG_COOKIE_SECURE=true and an HTTPS MG_APP_ORIGIN")
        return self


@lru_cache
def settings() -> Settings:
    return Settings()
