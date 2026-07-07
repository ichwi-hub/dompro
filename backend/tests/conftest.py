"""Pytest fixtures: изолированная тестовая БД."""

from __future__ import annotations

import os
import sys
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

# --- Переключение на TEST_DATABASE_URL до импорта приложения ---
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
BACKEND_ROOT = PROJECT_ROOT / "backend"
sys.path.insert(0, str(BACKEND_ROOT))

from dotenv import load_dotenv

load_dotenv(PROJECT_ROOT / ".env")


def _resolve_test_database_url() -> str:
    explicit = os.getenv("TEST_DATABASE_URL", "").strip()
    if explicit:
        return explicit
    base = os.getenv("DATABASE_URL", "")
    if "/dompro_test" in base:
        return base
    return base.replace("/dompro", "/dompro_test", 1)


os.environ["DATABASE_URL"] = _resolve_test_database_url()

from core.config import get_settings

get_settings.cache_clear()

from core import database as db_module
from core.pg_connect import sqlalchemy_async_url, sqlalchemy_connect_args
from core.security import create_access_token
from httpx import ASGITransport, AsyncClient
import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from core.database import get_db
from main import app
from models.client import Client
from models.enums import UserRole, VerificationStatus
from models.expert import Expert
from models.user import User

_settings = get_settings()
_test_engine = create_async_engine(
    sqlalchemy_async_url(_settings.DATABASE_URL),
    pool_pre_ping=True,
    connect_args=sqlalchemy_connect_args(_settings.DATABASE_URL),
)
TestSessionLocal = async_sessionmaker(
    bind=_test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

db_module.engine = _test_engine
db_module.AsyncSessionLocal = TestSessionLocal


async def _override_get_db():
    async with TestSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


app.dependency_overrides[get_db] = _override_get_db


@pytest.fixture(scope="session", autouse=True)
def reset_test_database():
  """Сброс схемы перед прогоном тестов."""
  import asyncio
  from scripts.setup_test_db import _test_url, reset_schema

  asyncio.run(reset_schema(_test_url(os.environ["DATABASE_URL"])))
  yield


@pytest_asyncio.fixture
async def db_session() -> AsyncSession:
    async with TestSessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def api_client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


def unique_identity(prefix: str) -> dict[str, str]:
    stamp = f"{prefix}_{uuid4().hex[:8]}"
    return {
        "email": f"{stamp}@dompro.ru",
        "phone": f"+79{uuid4().int % 10_000_000_000:010d}",
        "password": "Test123456",
    }


async def register_expert(api_client: AsyncClient, prefix: str) -> dict[str, str]:
    identity = unique_identity(prefix)
    resp = await api_client.post("/api/v1/auth/register", json=identity)
    assert resp.status_code == 201, resp.text
    login = await api_client.post(
        "/api/v1/auth/login",
        json={"login": identity["email"], "password": identity["password"]},
    )
    assert login.status_code == 200, login.text
    identity["token"] = login.json()["access_token"]
    return identity


async def register_client(api_client: AsyncClient, prefix: str) -> dict[str, str]:
    identity = unique_identity(prefix)
    resp = await api_client.post(
        "/api/v1/auth/register-client",
        json={**identity, "full_name": f"Client {prefix}"},
    )
    assert resp.status_code == 201, resp.text
    login = await api_client.post(
        "/api/v1/auth/login",
        json={"login": identity["email"], "password": identity["password"]},
    )
    assert login.status_code == 200, login.text
    identity["token"] = login.json()["access_token"]
    return identity


@pytest_asyncio.fixture
async def test_expert(api_client: AsyncClient) -> dict[str, str]:
    return await register_expert(api_client, "fixture_expert")


@pytest_asyncio.fixture
async def test_client(api_client: AsyncClient) -> dict[str, str]:
    return await register_client(api_client, "fixture_client")


@pytest_asyncio.fixture
async def auth_headers_expert(test_expert: dict[str, str]) -> dict[str, str]:
    return {"Authorization": f"Bearer {test_expert['token']}"}


@pytest_asyncio.fixture
async def auth_headers_client(test_client: dict[str, str]) -> dict[str, str]:
    return {"Authorization": f"Bearer {test_client['token']}"}


async def set_expert_verified_balance(
    *,
    email: str,
    balance: Decimal,
) -> None:
    async with TestSessionLocal() as db:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one()
        user.verification_status = VerificationStatus.VERIFIED
        user.updated_at = datetime.now(UTC)

        expert_result = await db.execute(select(Expert).where(Expert.user_id == user.id))
        expert = expert_result.scalar_one()
        expert.balance = balance
        expert.updated_at = datetime.now(UTC)

        await db.commit()


async def get_expert_by_email(email: str) -> Expert:
    async with TestSessionLocal() as db:
        result = await db.execute(
            select(Expert).join(User, User.id == Expert.user_id).where(User.email == email)
        )
        return result.scalar_one()


async def ensure_client_profile_for_user(email: str) -> int:
    async with TestSessionLocal() as db:
        user_result = await db.execute(select(User).where(User.email == email))
        user = user_result.scalar_one()

        existing = await db.execute(select(Client).where(Client.user_id == user.id))
        client = existing.scalar_one_or_none()
        if client is None:
            client = Client(user_id=user.id, company_name="Self Client")
            db.add(client)
            await db.flush()
        await db.commit()
        return client.id
