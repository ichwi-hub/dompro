from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    """Настройки приложения DomPro из переменных окружения и .env."""

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_NAME: str = "DomPro API"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False

    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/dompro"
    TEST_DATABASE_URL: str | None = None

    SECRET_KEY: str = "change-me-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # Хранилище файлов: local (ФС) | s3 (будущее object storage)
    STORAGE_BACKEND: str = "local"
    LOCAL_STORAGE_PATH: str = "./data/storage"
    API_PUBLIC_URL: str = "http://127.0.0.1:8000"
    STORAGE_MIN_FREE_GB: float = 2.0

    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5500",
        "http://127.0.0.1:5500",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "null",
    ]

    @property
    def local_storage_root(self) -> Path:
        p = Path(self.LOCAL_STORAGE_PATH)
        if not p.is_absolute():
            p = PROJECT_ROOT / p
        return p

    def file_public_url(self, key: str) -> str:
        base = self.API_PUBLIC_URL.rstrip("/")
        safe = key.replace("\\", "/").lstrip("/")
        return f"{base}/api/v1/files/{safe}"

    @property
    def database_url_sync(self) -> str:
        if self.DATABASE_URL.startswith("postgresql://"):
            return self.DATABASE_URL.replace(
                "postgresql://",
                "postgresql+psycopg2://",
                1,
            )
        return self.DATABASE_URL

    @property
    def database_url_async(self) -> str:
        if self.DATABASE_URL.startswith("postgresql://"):
            return self.DATABASE_URL.replace(
                "postgresql://",
                "postgresql+asyncpg://",
                1,
            )
        if "+psycopg2" in self.DATABASE_URL:
            return self.DATABASE_URL.replace("+psycopg2", "+asyncpg", 1)
        return self.DATABASE_URL


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
