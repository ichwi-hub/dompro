from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ClientCreate(BaseModel):
    """Создание профиля заказчика."""

    company_name: str | None = Field(default=None, max_length=255)


class ClientResponse(BaseModel):
    """Публичное представление заказчика."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    company_name: str | None


class ExpertClientListItem(BaseModel):
    """Элемент списка клиентов эксперта (без контактов)."""

    id: int
    full_name: str
    company_name: str | None
    accepted_orders_count: int
    last_order_title: str | None
    last_activity_at: datetime | None


class ExpertClientDetail(BaseModel):
    """Детали клиента для эксперта (без email и телефона)."""

    id: int
    full_name: str
    company_name: str | None
    accepted_orders_count: int
    accepted_responses_count: int
    last_order_title: str | None
    last_activity_at: datetime | None


class ExpertClientListResponse(BaseModel):
    """Список клиентов эксперта."""

    items: list[ExpertClientListItem]
