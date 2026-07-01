from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.dependencies import get_current_expert
from models.expert import Expert
from models.user import User
from schemas.expert import ExpertProfileResponse, ExpertProfileUpdate

router = APIRouter(prefix="/expert", tags=["Профиль эксперта"])


def _build_profile_response(expert: Expert) -> ExpertProfileResponse:
    """Сборка ответа профиля с учётом статуса верификации пользователя."""
    user: User = expert.user
    return ExpertProfileResponse(
        id=expert.id,
        user_id=expert.user_id,
        full_name=expert.full_name,
        photo_url=expert.photo_url,
        experience_years=expert.experience_years,
        specialization=expert.specialization,
        description=expert.description,
        rating=expert.rating,
        balance=expert.balance,
        inn=expert.inn,
        verification_status=user.verification_status,
        is_profile_complete=expert.is_profile_complete,
        verified_at=expert.verified_at,
        rejection_reason=expert.rejection_reason,
        created_at=expert.created_at,
        updated_at=expert.updated_at,
    )


@router.get("/profile", response_model=ExpertProfileResponse)
async def get_expert_profile(
    expert: Expert = Depends(get_current_expert),
) -> ExpertProfileResponse:
    """Получить профиль текущего эксперта."""
    return _build_profile_response(expert)


@router.put("/profile", response_model=ExpertProfileResponse)
async def update_expert_profile(
    payload: ExpertProfileUpdate,
    expert: Expert = Depends(get_current_expert),
    db: AsyncSession = Depends(get_db),
) -> ExpertProfileResponse:
    """Этап 2: обновление профиля эксперта.

    Обязательны: full_name, experience_years, specialization, description.
    photo_url — опционально.
    """
    expert.full_name = payload.full_name
    expert.experience_years = payload.experience_years
    expert.specialization = payload.specialization
    expert.description = payload.description
    expert.category = payload.specialization
    expert.updated_at = datetime.now(timezone.utc)

    if payload.photo_url is not None:
        expert.photo_url = payload.photo_url

    if expert.user:
        expert.user.full_name = payload.full_name
        expert.user.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(expert)
    return _build_profile_response(expert)
