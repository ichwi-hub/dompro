from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from models.enums import OrderStatus, ResponseStatus


class ResponseCreate(BaseModel):
    """Отклик эксперта на заказ (стоимость лида фиксирована платформой)."""

    message: str | None = Field(default=None, max_length=5000)


class ResponseResponse(BaseModel):
    """Ответ с данными отклика."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    order_id: int
    expert_id: int
    message: str | None
    cost: Decimal
    status: ResponseStatus
    created_at: datetime


class ExpertBrief(BaseModel):
    """Краткие данные эксперта для клиента (без контактов)."""

    id: int
    full_name: str | None
    specialization: str | None
    rating: Decimal
    experience_years: int


class ResponseWithExpertResponse(ResponseResponse):
    """Отклик с данными эксперта."""

    expert: ExpertBrief


class OrderBrief(BaseModel):
    """Краткие данные заказа для истории откликов эксперта."""

    id: int
    title: str
    status: OrderStatus
    category: str


class ExpertResponseHistoryItem(ResponseResponse):
    """Отклик эксперта с данными заказа."""

    order: OrderBrief
