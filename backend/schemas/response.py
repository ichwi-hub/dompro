from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from models.enums import ResponseStatus


class ResponseCreate(BaseModel):
    """Отклик эксперта на заказ."""

    message: str | None = None
    cost: Decimal = Field(ge=0)


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
