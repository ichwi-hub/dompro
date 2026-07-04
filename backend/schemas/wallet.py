from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from schemas.transaction import TransactionResponse


class WalletBalanceResponse(BaseModel):
    """Текущий баланс кошелька эксперта."""

    balance: Decimal
    currency: str = "RUB"


class WalletTopUpRequest(BaseModel):
    """Запрос на пополнение баланса (заглушка, без реальной оплаты)."""

    amount: Decimal = Field(gt=0, description="Сумма пополнения в рублях")


class WalletTopUpResponse(BaseModel):
    """Результат пополнения баланса."""

    balance: Decimal
    message: str = "Баланс пополнен"


class WalletResponse(BaseModel):
    """Состояние внутреннего кошелька эксперта (legacy)."""

    model_config = ConfigDict(from_attributes=True)

    expert_id: int
    balance: Decimal


class WalletTransactionsResponse(BaseModel):
    """Список транзакций кошелька."""

    items: list[TransactionResponse]
