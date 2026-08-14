from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "app" / "data"
UPLOAD_DIR = BASE_DIR / "uploads"
DB_DIR = BASE_DIR / "db"
DB_PATH = DB_DIR / "esg_copilot.db"

UPLOAD_DIR.mkdir(exist_ok=True)
DB_DIR.mkdir(exist_ok=True)


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
