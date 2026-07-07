from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from models.enums import ContractStatus


class ContractResponse(BaseModel):
    """Ответ с данными договора."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    order_id: int
    expert_id: int
    client_id: int
    pdf_path: str
    status: ContractStatus
    signed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ExpertContractListItem(BaseModel):
    """Договор в списке workspace эксперта."""

    id: int
    order_id: int
    order_title: str
    client_name: str
    status: ContractStatus
    created_at: datetime
    pdf_path: str


class ExpertContractListResponse(BaseModel):
    items: list[ExpertContractListItem]
    total: int
