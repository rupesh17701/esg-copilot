import os
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "app" / "data"

# STORAGE_DIR lets a deployment with a single mountable volume (e.g. Railway,
# which allows only one persistent volume per service) point both the SQLite
# DB and uploaded files at subdirectories of that one mount. Local/dev and
# docker-compose (two separate volumes) don't set it, so they keep the
# original separate backend/db and backend/uploads directories.
_storage_dir = os.environ.get("STORAGE_DIR")
if _storage_dir:
    UPLOAD_DIR = Path(_storage_dir) / "uploads"
    DB_DIR = Path(_storage_dir) / "db"
else:
    UPLOAD_DIR = BASE_DIR / "uploads"
    DB_DIR = BASE_DIR / "db"
DB_PATH = DB_DIR / "esg_copilot.db"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
DB_DIR.mkdir(parents=True, exist_ok=True)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-opus-5"
    database_url: str = f"sqlite:///{DB_PATH}"
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    @property
    def llm_configured(self) -> bool:
        return bool(self.anthropic_api_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()
