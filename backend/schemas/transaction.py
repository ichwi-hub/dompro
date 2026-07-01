from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from models.enums import TransactionType


class TransactionCreate(BaseModel):
    """Создание транзакции (пополнение или списание за отклик)."""

    type: TransactionType
    amount: Decimal = Field(gt=0)
    description: str | None = None


class TransactionResponse(BaseModel):
    """Ответ с данными транзакции."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    expert_id: int
    type: TransactionType
    amount: Decimal
    description: str | None
    created_at: datetime
