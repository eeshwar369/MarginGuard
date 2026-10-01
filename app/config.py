from functools import lru_cache
from pathlib import Path

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="MG_", env_file=".env", extra="ignore")
    env: str = "development"
    data_dir: Path = Path("data")
    static_dir: Path = Path("web/out")
    app_origin: str = "http://localhost:3000"
    cookie_secure: bool = False
    allow_registration: bool = True
    allow_demo: bool = True
    max_upload_mb: int = Field(8, ge=1, le=50)
    max_rows: int = Field(50000, ge=100, le=200000)
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    ai_timeout_seconds: int = Field(35, ge=5, le=90)

    @model_validator(mode="after")
    def production_config(self):
        if self.env == "production" and (
            not self.cookie_secure or not self.app_origin.startswith("https://")
        ):
            raise ValueError("Production requires MG_COOKIE_SECURE=true and an HTTPS MG_APP_ORIGIN")
        return self


@lru_cache
def settings() -> Settings:
    return Settings()
