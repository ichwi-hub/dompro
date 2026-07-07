from contextlib import asynccontextmanager
import logging

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

import models  # noqa: F401 — регистрация ORM-моделей
from api.v1 import (
    admin,
    auth,
    contracts,
    expert_clients,
    expert_feed,
    expert_profile,
    files,
    orders,
    responses,
    verification,
    wallet,
)
from core.config import settings
from core.database import get_db
from core.storage.disk_monitor import warn_if_low_disk

logger = logging.getLogger(__name__)

API_V1_PREFIX = "/api/v1"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Жизненный цикл приложения."""
    if settings.STORAGE_BACKEND.lower() == "local":
        storage_root = settings.local_storage_root
        storage_root.mkdir(parents=True, exist_ok=True)
        report = warn_if_low_disk(
            storage_root,
            min_free_gb=settings.STORAGE_MIN_FREE_GB,
        )
        logger.info("Storage disk: %s", report)
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
app.include_router(wallet.router, prefix=f"{API_V1_PREFIX}/wallet")
app.include_router(orders.router, prefix=f"{API_V1_PREFIX}/orders")
app.include_router(responses.router, prefix=API_V1_PREFIX)
app.include_router(expert_clients.router, prefix=API_V1_PREFIX)
app.include_router(expert_feed.router, prefix=API_V1_PREFIX)
app.include_router(contracts.router, prefix=API_V1_PREFIX)
app.include_router(files.router, prefix=API_V1_PREFIX)


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
