from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
from functools import lru_cache
from typing import Literal


class Settings(BaseSettings):
    """
    Central settings for Bergie.
    All values are loaded from environment variables / .env file.
    Pydantic validates types automatically — if APP_PORT is not an int,
    the app refuses to start rather than failing mysteriously later.
    """

    # ── Application ────────────────────────────────────────────────
    APP_ENV: Literal["development", "staging", "production"] = "development"
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    SECRET_KEY: str
    API_V1_PREFIX: str = "/api/v1"
    PROJECT_NAME: str = "Bergie — EduBerg AI Assistant"

    # ── Database ───────────────────────────────────────────────────
    DATABASE_URL: str

    # ── Redis ──────────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"
    SESSION_TTL_SECONDS: int = 86400          # 24 hours

    # ── Anthropic (Claude) ─────────────────────────────────────────
    ANTHROPIC_API_KEY: str
    ANTHROPIC_MODEL: str = "claude-haiku-4-5-20251001"  # fast + affordable
    ANTHROPIC_MAX_TOKENS: int = 1024

    # ── Telegram ───────────────────────────────────────────────────
    TELEGRAM_BOT_TOKEN: str
    TELEGRAM_WEBHOOK_SECRET: str = ""
    TELEGRAM_API_BASE: str = "https://api.telegram.org"

    # ── Bergie Persona ─────────────────────────────────────────────
    BERGIE_NAME: str = "Bergie"
    BERGIE_COMPANY: str = "EduBerg Learning Hub"

    @field_validator("SECRET_KEY")
    @classmethod
    def secret_key_must_be_strong(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters")
        return v

    @field_validator("DATABASE_URL")
    @classmethod
    def database_url_must_be_postgres(cls, v: str) -> str:
        if not v.startswith("postgresql"):
            raise ValueError("DATABASE_URL must be a PostgreSQL connection string")
        return v

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

@lru_cache()
def get_settings() -> Settings:
    """
    Returns a cached Settings instance.
    The @lru_cache means this is only constructed once per process —
    we don't re-read the .env file on every request.
    """
    return Settings()


# Convenience shortcut used throughout the codebase
settings = get_settings()