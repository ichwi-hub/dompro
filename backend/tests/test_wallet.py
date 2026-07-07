from decimal import Decimal

import pytest
from sqlalchemy import select

from core.database import AsyncSessionLocal
from models.enums import TransactionType
from models.expert import Expert
from models.transaction import Transaction
from models.user import User
from tests.conftest import register_client, register_expert, set_expert_verified_balance


@pytest.mark.asyncio
async def test_topup_increases_balance(api_client):
    expert = await register_expert(api_client, "wallet_topup_expert")
    await set_expert_verified_balance(email=expert["email"], balance=Decimal("200.00"))

    topup = await api_client.post(
        "/api/v1/wallet/topup",
        headers={"Authorization": f"Bearer {expert['token']}"},
        json={"amount": "300.00"},
    )
    assert topup.status_code == 200, topup.text
    assert Decimal(topup.json()["balance"]) == Decimal("500.00")


@pytest.mark.asyncio
async def test_wallet_transactions_include_response_fee_and_amount(api_client):
    client_user = await register_client(api_client, "wallet_resp_client")
    order = await api_client.post(
        "/api/v1/orders",
        headers={"Authorization": f"Bearer {client_user['token']}"},
        json={"title": "Кошелек и отклик", "description": "Проверяем транзакцию списания", "category": "Юрист"},
    )
    order_id = order.json()["id"]

    expert = await register_expert(api_client, "wallet_resp_expert")
    await set_expert_verified_balance(email=expert["email"], balance=Decimal("400.00"))

    created_response = await api_client.post(
        f"/api/v1/orders/{order_id}/responses",
        headers={"Authorization": f"Bearer {expert['token']}"},
        json={"message": "Отклик для проверки кошелька"},
    )
    assert created_response.status_code == 201, created_response.text

    balance = await api_client.get(
        "/api/v1/wallet/balance",
        headers={"Authorization": f"Bearer {expert['token']}"},
    )
    assert balance.status_code == 200, balance.text
    assert Decimal(balance.json()["balance"]) == Decimal("250.00")

    history = await api_client.get(
        "/api/v1/wallet/transactions",
        headers={"Authorization": f"Bearer {expert['token']}"},
    )
    assert history.status_code == 200, history.text
    fee_tx = [item for item in history.json()["items"] if item["type"] == "response_fee"]
    assert fee_tx, history.text
    assert Decimal(fee_tx[0]["amount"]) == Decimal("150.00")


@pytest.mark.asyncio
async def test_topup_creates_deposit_transaction(api_client):
    expert = await register_expert(api_client, "wallet_deposit_expert")
    await set_expert_verified_balance(email=expert["email"], balance=Decimal("0.00"))

    topup = await api_client.post(
        "/api/v1/wallet/topup",
        headers={"Authorization": f"Bearer {expert['token']}"},
        json={"amount": "175.00"},
    )
    assert topup.status_code == 200, topup.text

    async with AsyncSessionLocal() as db:
        user_row = await db.execute(select(User).where(User.email == expert["email"]))
        user = user_row.scalar_one()

        expert_row = await db.execute(select(Expert).where(Expert.user_id == user.id))
        expert_model = expert_row.scalar_one()
        assert Decimal(str(expert_model.balance)) == Decimal("175.00")

        tx_row = await db.execute(
            select(Transaction).where(
                Transaction.expert_id == expert_model.id,
                Transaction.type == TransactionType.DEPOSIT,
            )
        )
        tx = tx_row.scalars().all()
        assert tx
        assert Decimal(str(tx[-1].amount)) == Decimal("175.00")
