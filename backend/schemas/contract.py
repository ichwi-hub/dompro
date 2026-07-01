from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ContractCreate(BaseModel):
    """Создание договора между сторонами."""

    order_id: int
    expert_id: int
    client_id: int
    pdf_url: str = Field(min_length=1)


class ContractResponse(BaseModel):
    """Ответ с данными договора."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    order_id: int
    expert_id: int
    client_id: int
    pdf_url: str
    signed_at: datetime | None
    created_at: datetime
