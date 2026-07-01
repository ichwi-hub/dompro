from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

import models  # noqa: F401 — регистрация ORM-моделей
from api.v1 import admin, auth, expert_profile, verification
from core.config import settings
from core.database import get_db

API_V1_PREFIX = "/api/v1"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Жизненный цикл приложения."""
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="API закрытого маркетплейса экспертов DomPro",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix=API_V1_PREFIX)
app.include_router(expert_profile.router, prefix=API_V1_PREFIX)
app.include_router(verification.router, prefix=API_V1_PREFIX)
app.include_router(admin.router, prefix=API_V1_PREFIX)


@app.get("/")
async def root() -> dict[str, str]:
    """Корневой эндпоинт: базовая информация о сервисе."""
    return {
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "ok",
    }


@app.get("/health")
async def health(db: AsyncSession = Depends(get_db)) -> dict[str, str]:
    """Проверка доступности API и подключения к PostgreSQL."""
    await db.execute(text("SELECT 1"))
    return {"status": "healthy", "database": "connected"}


@app.get(f"{API_V1_PREFIX}/test")
async def api_test() -> dict[str, str]:
    """Тестовый эндпоинт API v1."""
    return {"message": "DomPro API is running"}
