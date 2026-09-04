from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent


def _path(name: str, default: str) -> Path:
    value = Path(os.getenv(name, default))
    return value if value.is_absolute() else BASE_DIR / value


@dataclass(frozen=True)
class Settings:
    app_env: str = os.getenv("APP_ENV", "development")
    secret_key: str = os.getenv("APP_SECRET_KEY", "local-development-key")
    owner_email: str = os.getenv("OWNER_EMAIL", "demo@lingua.local")
    owner_password: str = os.getenv("OWNER_PASSWORD", "demo123")
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
    youtube_api_key: str = os.getenv("YOUTUBE_API_KEY", "")
    obsidian_path: Path = _path("OBSIDIAN_VAULT_PATH", "obsidian-vault")
    database_path: Path = _path("DATABASE_PATH", "data/lingua360.db")
    voice_path: Path = _path("VOICE_STORAGE_PATH", "data/voices")
    telegram_enabled: bool = os.getenv("TELEGRAM_ENABLED", "false").lower() == "true"


settings = Settings()

