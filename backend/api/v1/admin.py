from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.database import get_db
from core.dependencies import get_current_admin
from models.enums import ExpertVerificationStatus, VerificationStatus
from models.expert import Expert
from models.user import User
from models.verification import ExpertVerification
from schemas.expert import ExpertProfileResponse
from schemas.order import OrderListResponse
from schemas.verification import ExpertVerificationResponse, VerificationRejectRequest

router = APIRouter(prefix="/admin", tags=["Администрирование"])


def _to_admin_response(item: ExpertVerification) -> ExpertVerificationResponse:
    expert = item.expert
    user = expert.user if expert else None
    return ExpertVerificationResponse(
        id=item.id,
        expert_id=item.expert_id,
        expert_full_name=expert.full_name if expert else None,
        expert_email=user.email if user else None,
        inn=item.inn,
        diploma_url=item.diploma_url,
        self_employment_url=item.self_employment_url,
        bar_association_url=item.bar_association_url,
        status=item.status,
        rejection_reason=item.rejection_reason,
        reviewed_at=item.reviewed_at,
        created_at=item.created_at,
    )


@router.get("/verifications", response_model=list[ExpertVerificationResponse])
async def list_pending_verifications(
    _: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> list[ExpertVerificationResponse]:
    """Список заявок на верификацию со статусом pending."""
    result = await db.execute(
        select(ExpertVerification)
        .options(
            selectinload(ExpertVerification.expert).selectinload(Expert.user)
        )
        .where(ExpertVerification.status == ExpertVerificationStatus.PENDING)
        .order_by(ExpertVerification.created_at.asc())
    )
    items = result.scalars().all()
    return [_to_admin_response(item) for item in items]


@router.put("/verifications/{verification_id}/approve", response_model=ExpertVerificationResponse)
async def approve_verification(
    verification_id: int,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> ExpertVerificationResponse:
    """Одобрить заявку: эксперт получает статус verified и может откликаться."""
    result = await db.execute(
        select(ExpertVerification)
        .options(
            selectinload(ExpertVerification.expert).selectinload(Expert.user)
        )
        .where(ExpertVerification.id == verification_id)
    )
    verification = result.scalar_one_or_none()
    if verification is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Заявка не найдена")

    if verification.status != ExpertVerificationStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Заявка уже обработана",
        )

    now = datetime.now(timezone.utc)
    verification.status = ExpertVerificationStatus.APPROVED
    verification.reviewed_by = admin.id
    verification.reviewed_at = now
    verification.updated_at = now

    expert = verification.expert
    expert.verified_by = admin.id
    expert.verified_at = now
    expert.rejection_reason = None
    expert.updated_at = now

    expert.user.verification_status = VerificationStatus.VERIFIED
    expert.user.updated_at = now

    await db.commit()
    await db.refresh(verification)
    return _to_admin_response(verification)


@router.get("/experts/{expert_id}", response_model=ExpertProfileResponse)
async def get_expert_for_admin(
    expert_id: int,
    _: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> ExpertProfileResponse:
    """Профиль эксперта для модерации."""
    from api.v1.expert_profile import _build_profile_response

    result = await db.execute(
        select(Expert)
        .options(selectinload(Expert.user))
        .where(Expert.id == expert_id)
    )
    expert = result.scalar_one_or_none()
    if expert is None:
        raise HTTPException(status_code=404, detail="Эксперт не найден")
    return _build_profile_response(expert)


@router.get("/orders", response_model=OrderListResponse)
async def list_orders_for_admin(
    page: int = 1,
    limit: int = 50,
    _: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> OrderListResponse:
    """Все заказы платформы (для администратора)."""
    from sqlalchemy import func
    from models.client import Client
    from models.order import Order

    query = select(Order).options(selectinload(Order.client).selectinload(Client.user))
    total = await db.scalar(select(func.count()).select_from(query.subquery())) or 0
    offset = (page - 1) * limit
    result = await db.execute(
        query.order_by(Order.created_at.desc()).offset(offset).limit(limit)
    )
    orders = result.scalars().all()

    from api.v1.orders import _order_to_response

    return OrderListResponse(
        items=[_order_to_response(o, show_client_name=True) for o in orders],
        total=total,
        page=page,
        limit=limit,
    )


@router.put("/verifications/{verification_id}/reject", response_model=ExpertVerificationResponse)
async def reject_verification(
    verification_id: int,
    payload: VerificationRejectRequest,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> ExpertVerificationResponse:
    """Отклонить заявку с указанием причины."""
    result = await db.execute(
        select(ExpertVerification)
        .options(
            selectinload(ExpertVerification.expert).selectinload(Expert.user)
        )
        .where(ExpertVerification.id == verification_id)
    )
    verification = result.scalar_one_or_none()
    if verification is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Заявка не найдена")

    if verification.status != ExpertVerificationStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Заявка уже обработана",
        )

    now = datetime.now(timezone.utc)
    verification.status = ExpertVerificationStatus.REJECTED
    verification.reviewed_by = admin.id
    verification.reviewed_at = now
    verification.rejection_reason = payload.rejection_reason
    verification.updated_at = now

    expert = verification.expert
    expert.rejection_reason = payload.rejection_reason
    expert.updated_at = now
    expert.user.verification_status = VerificationStatus.REJECTED
    expert.user.updated_at = now

    await db.commit()
    await db.refresh(verification)
    return _to_admin_response(verification)
