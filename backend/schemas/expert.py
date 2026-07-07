from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from models.enums import VerificationStatus


class ExpertProfileUpdate(BaseModel):
    """Этап 2: заполнение профиля эксперта."""

    full_name: str = Field(min_length=2, max_length=255)
    experience_years: int = Field(ge=0, le=60)
    specialization: str = Field(min_length=2, max_length=255)
    description: str = Field(min_length=10)
    education: str | None = None
    photo_url: str | None = None


class ExpertProfileResponse(BaseModel):
    """Профиль эксперта."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    full_name: str | None
    photo_url: str | None
    experience_years: int
    specialization: str | None
    education: str | None
    description: str | None
    rating: Decimal
    balance: Decimal
    inn: str | None
    verification_status: VerificationStatus
    is_profile_complete: bool
    verified_at: datetime | None
    rejection_reason: str | None
    created_at: datetime
    updated_at: datetime
