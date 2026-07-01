from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from models.enums import OrderStatus


class OrderCreate(BaseModel):
    """Создание заказа клиентом."""

    title: str = Field(min_length=3, max_length=255)
    description: str | None = None
    category: str = Field(min_length=2, max_length=128)
    budget: Decimal | None = Field(default=None, ge=0)


class OrderResponse(BaseModel):
    """Ответ с данными заказа."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    client_id: int
    title: str
    description: str | None
    category: str
    budget: Decimal | None
    status: OrderStatus
    created_at: datetime
