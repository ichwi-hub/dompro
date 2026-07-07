from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from core.database import AsyncSessionLocal
from main import app
from models.client import Client
from models.enums import VerificationStatus
from models.expert import Expert
from models.user import User


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
    resp = await api_client.post(
        "/api/v1/auth/register",
        json=identity,
    )
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


async def set_expert_verified_balance(
    *,
    email: str,
    balance: Decimal,
) -> None:
    async with AsyncSessionLocal() as db:
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
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Expert).join(User, User.id == Expert.user_id).where(User.email == email)
        )
        return result.scalar_one()


async def ensure_client_profile_for_user(email: str) -> int:
    async with AsyncSessionLocal() as db:
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
