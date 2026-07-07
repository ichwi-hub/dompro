from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from models.enums import OrderStatus, ResponseStatus


class ExpertFeedItem(BaseModel):
    """Элемент ленты заказов эксперта."""

    model_config = ConfigDict(from_attributes=True)

    order_id: int
    title: str
    description: str | None
    budget: Decimal | None
    deadline: date | None
    status: OrderStatus
    has_response: bool
    response_status: ResponseStatus | None


class ExpertFeedResponse(BaseModel):
    items: list[ExpertFeedItem]
    total: int
