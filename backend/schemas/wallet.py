from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class WalletResponse(BaseModel):
    """Состояние внутреннего кошелька эксперта."""

    model_config = ConfigDict(from_attributes=True)

    expert_id: int
    balance: Decimal
