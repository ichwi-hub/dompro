"""API внутреннего кошелька эксперта: баланс, пополнение, история."""

from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.constants import CURRENCY_RUB
from core.database import get_db
from core.dependencies import get_current_expert
from models.enums import TransactionType
from models.expert import Expert
from models.transaction import Transaction
from schemas.transaction import TransactionResponse
from schemas.wallet import (
    WalletBalanceResponse,
    WalletTopUpRequest,
    WalletTopUpResponse,
    WalletTransactionsResponse,
)

router = APIRouter(tags=["Кошелёк"])


@router.get("/balance", response_model=WalletBalanceResponse)
async def get_balance(
    expert: Expert = Depends(get_current_expert),
) -> WalletBalanceResponse:
    """Текущий баланс эксперта для оплаты откликов."""
    return WalletBalanceResponse(balance=expert.balance, currency=CURRENCY_RUB)


@router.get("/transactions", response_model=WalletTransactionsResponse)
async def get_transactions(
    expert: Expert = Depends(get_current_expert),
    db: AsyncSession = Depends(get_db),
) -> WalletTransactionsResponse:
    """История пополнений и списаний за отклики (новые сначала)."""
    result = await db.execute(
        select(Transaction)
        .where(Transaction.expert_id == expert.id)
        .order_by(Transaction.created_at.desc())
    )
    items = result.scalars().all()
    return WalletTransactionsResponse(
        items=[TransactionResponse.model_validate(t) for t in items]
    )


@router.post("/topup", response_model=WalletTopUpResponse)
async def topup_balance(
    payload: WalletTopUpRequest,
    expert: Expert = Depends(get_current_expert),
    db: AsyncSession = Depends(get_db),
) -> WalletTopUpResponse:
    """Пополнение баланса (заглушка без ЮKassa).

    В продакшене здесь будет интеграция с платёжным шлюзом.
    """
    expert.balance = Decimal(str(expert.balance)) + payload.amount

    transaction = Transaction(
        expert_id=expert.id,
        type=TransactionType.DEPOSIT,
        amount=payload.amount,
        description="Пополнение баланса",
    )
    db.add(transaction)
    await db.commit()
    await db.refresh(expert)

    return WalletTopUpResponse(balance=expert.balance)
