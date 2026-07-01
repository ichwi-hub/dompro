from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from models.enums import ExpertVerificationStatus, VerificationStatus


class VerificationStatusResponse(BaseModel):
    """Статус верификации текущего эксперта."""

    verification_status: VerificationStatus
    latest_request_status: ExpertVerificationStatus | None = None
    rejection_reason: str | None = None
    is_profile_complete: bool
    can_submit: bool


class VerificationRejectRequest(BaseModel):
    """Причина отклонения заявки администратором."""

    rejection_reason: str = Field(min_length=5, max_length=1000)


class ExpertVerificationResponse(BaseModel):
    """Заявка на верификацию (для админ-панели)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    expert_id: int
    expert_full_name: str | None = None
    expert_email: str | None = None
    inn: str
    diploma_url: str
    self_employment_url: str
    bar_association_url: str | None
    status: ExpertVerificationStatus
    rejection_reason: str | None
    reviewed_at: datetime | None
    created_at: datetime
