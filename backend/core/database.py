import ssl
from collections.abc import AsyncGenerator
from urllib.parse import urlparse

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from core.config import settings


class Base(DeclarativeBase):
    """Базовый класс для всех ORM-моделей DomPro."""

    pass


def _build_connect_args() -> dict:
    """SSL-параметры для Supabase и других облачных PostgreSQL."""
    host = urlparse(settings.DATABASE_URL).hostname or ""
    if "supabase.com" in host:
        ssl_context = ssl.create_default_context()
        # Supabase pooler: на части окружений Windows цепочка сертификатов
        # не проходит verify; подключение при этом шифруется.
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        return {
            "ssl": ssl_context,
            # PgBouncer (порт 6543) не поддерживает prepared statements
            "statement_cache_size": 0,
        }
    return {}


engine = create_async_engine(
    settings.database_url_async,
    pool_pre_ping=True,
    echo=settings.DEBUG,
    connect_args=_build_connect_args(),
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Зависимость FastAPI: асинхронная сессия БД на один запрос."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
