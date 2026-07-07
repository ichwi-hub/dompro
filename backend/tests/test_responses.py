from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy import select

from tests.conftest import TestSessionLocal
from models.enums import OrderStatus, ResponseStatus, TransactionType
from models.expert import Expert
from models.order import Order
from models.response import Response
from models.transaction import Transaction
from models.user import User
from tests.conftest import (
    ensure_client_profile_for_user,
    register_client,
    register_expert,
    set_expert_verified_balance,
)


@pytest.mark.asyncio
async def test_verified_expert_can_respond_unverified_cannot(api_client):
    client_user = await register_client(api_client, "resp_perm_client")
    order = await api_client.post(
        "/api/v1/orders",
        headers={"Authorization": f"Bearer {client_user['token']}"},
        json={"title": "Заказ для отклика", "description": "Нужен ответ эксперта", "category": "Право"},
    )
    order_id = order.json()["id"]

    unverified = await register_expert(api_client, "resp_perm_unverified")
    forbidden = await api_client.post(
        f"/api/v1/orders/{order_id}/responses",
        headers={"Authorization": f"Bearer {unverified['token']}"},
        json={"message": "Готов помочь"},
    )
    assert forbidden.status_code == 403

    verified = await register_expert(api_client, "resp_perm_verified")
    await set_expert_verified_balance(email=verified["email"], balance=Decimal("1000.00"))

    success = await api_client.post(
        f"/api/v1/orders/{order_id}/responses",
        headers={"Authorization": f"Bearer {verified['token']}"},
        json={"message": "Берусь за работу"},
    )
    assert success.status_code == 201, success.text
    assert Decimal(success.json()["cost"]) == Decimal("150.00")


@pytest.mark.asyncio
async def test_response_fee_is_charged_once_and_duplicate_rejected(api_client):
    client_user = await register_client(api_client, "resp_fee_client")
    order = await api_client.post(
        "/api/v1/orders",
        headers={"Authorization": f"Bearer {client_user['token']}"},
        json={"title": "Отклик с комиссией", "description": "Проверяем списание fee", "category": "Бухучет"},
    )
    order_id = order.json()["id"]

    expert = await register_expert(api_client, "resp_fee_expert")
    await set_expert_verified_balance(email=expert["email"], balance=Decimal("500.00"))

    first = await api_client.post(
        f"/api/v1/orders/{order_id}/responses",
        headers={"Authorization": f"Bearer {expert['token']}"},
        json={"message": "Первый отклик"},
    )
    assert first.status_code == 201, first.text

    second = await api_client.post(
        f"/api/v1/orders/{order_id}/responses",
        headers={"Authorization": f"Bearer {expert['token']}"},
        json={"message": "Второй отклик"},
    )
    assert second.status_code == 400

    async with TestSessionLocal() as db:
        user_row = await db.execute(select(User).where(User.email == expert["email"]))
        user = user_row.scalar_one()
        expert_row = await db.execute(select(Expert).where(Expert.user_id == user.id))
        expert_model = expert_row.scalar_one()
        tx_rows = await db.execute(
            select(Transaction).where(
                Transaction.expert_id == expert_model.id,
                Transaction.type == TransactionType.RESPONSE_FEE,
            )
        )
        tx_items = tx_rows.scalars().all()
        assert len(tx_items) == 1

        assert Decimal(str(expert_model.balance)) == Decimal("350.00")


@pytest.mark.asyncio
async def test_expert_cannot_respond_to_own_order(api_client):
    expert = await register_expert(api_client, "resp_own_expert")
    await set_expert_verified_balance(email=expert["email"], balance=Decimal("1000.00"))
    client_id = await ensure_client_profile_for_user(expert["email"])

    async with TestSessionLocal() as db:
        user_result = await db.execute(select(User).where(User.email == expert["email"]))
        user = user_result.scalar_one()
        user.updated_at = datetime.now(UTC)

        own_order = Order(
            client_id=client_id,
            title="Собственный заказ",
            description="На него нельзя откликаться самому",
            category="Юриспруденция",
            status=OrderStatus.OPEN,
        )
        db.add(own_order)
        await db.commit()
        await db.refresh(own_order)
        order_id = own_order.id

    blocked = await api_client.post(
        f"/api/v1/orders/{order_id}/responses",
        headers={"Authorization": f"Bearer {expert['token']}"},
        json={"message": "Попытка отклика на свой заказ"},
    )
    assert blocked.status_code == 400


@pytest.mark.asyncio
async def test_accept_one_response_rejects_others_and_moves_order(api_client):
    client_user = await register_client(api_client, "resp_accept_client")
    order = await api_client.post(
        "/api/v1/orders",
        headers={"Authorization": f"Bearer {client_user['token']}"},
        json={"title": "Выбор исполнителя", "description": "Два эксперта, один победитель", "category": "Маркетинг"},
    )
    order_id = order.json()["id"]

    expert_a = await register_expert(api_client, "resp_accept_a")
    expert_b = await register_expert(api_client, "resp_accept_b")
    await set_expert_verified_balance(email=expert_a["email"], balance=Decimal("1000.00"))
    await set_expert_verified_balance(email=expert_b["email"], balance=Decimal("1000.00"))

    resp_a = await api_client.post(
        f"/api/v1/orders/{order_id}/responses",
        headers={"Authorization": f"Bearer {expert_a['token']}"},
        json={"message": "Отклик A"},
    )
    resp_b = await api_client.post(
        f"/api/v1/orders/{order_id}/responses",
        headers={"Authorization": f"Bearer {expert_b['token']}"},
        json={"message": "Отклик B"},
    )
    assert resp_a.status_code == 201, resp_a.text
    assert resp_b.status_code == 201, resp_b.text

    accept = await api_client.put(
        f"/api/v1/responses/{resp_a.json()['id']}/accept",
        headers={"Authorization": f"Bearer {client_user['token']}"},
    )
    assert accept.status_code == 200, accept.text
    assert accept.json()["status"] == "accepted"

    async with TestSessionLocal() as db:
        rows = await db.execute(select(Response).where(Response.order_id == order_id))
        items = rows.scalars().all()
        statuses = {item.id: item.status for item in items}
        assert statuses[resp_a.json()["id"]] == ResponseStatus.ACCEPTED
        assert statuses[resp_b.json()["id"]] == ResponseStatus.REJECTED

        order_row = await db.execute(select(Order).where(Order.id == order_id))
        updated_order = order_row.scalar_one()
        assert updated_order.status == OrderStatus.IN_PROGRESS
