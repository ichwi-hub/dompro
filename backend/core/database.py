from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from core.config import settings
from core.pg_connect import sqlalchemy_async_url, sqlalchemy_connect_args


class Base(DeclarativeBase):
    """Базовый класс для всех ORM-моделей DomPro."""

    pass


engine = create_async_engine(
    sqlalchemy_async_url(settings.DATABASE_URL),
    pool_pre_ping=True,
    echo=settings.DEBUG,
    connect_args=sqlalchemy_connect_args(settings.DATABASE_URL),
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
