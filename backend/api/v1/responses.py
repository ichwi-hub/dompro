"""API откликов экспертов: создание, принятие/отклонение, история."""

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.constants import RESPONSE_FEE
from core.database import get_db
from core.dependencies import get_current_client, get_current_expert, get_verified_expert
from models.client import Client
from models.enums import OrderStatus, ResponseStatus, TransactionType
from models.expert import Expert
from models.order import Order
from models.response import Response
from models.transaction import Transaction
from schemas.response import (
    ExpertBrief,
    ExpertResponseHistoryItem,
    OrderBrief,
    ResponseCreate,
    ResponseResponse,
    ResponseWithExpertResponse,
)

router = APIRouter(tags=["Отклики"])


def _expert_brief(expert: Expert) -> ExpertBrief:
    return ExpertBrief(
        id=expert.id,
        full_name=expert.full_name,
        specialization=expert.specialization,
        rating=expert.rating,
        experience_years=expert.experience_years,
    )


@router.post(
    "/orders/{order_id}/responses",
    response_model=ResponseResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_response(
    order_id: int,
    payload: ResponseCreate,
    expert: Expert = Depends(get_verified_expert),
    db: AsyncSession = Depends(get_db),
) -> ResponseResponse:
    """Откликнуться на заказ.

    Атомарно: проверки → списание 150 ₽ → транзакция → отклик.
    """
    result = await db.execute(
        select(Order)
        .options(selectinload(Order.client))
        .where(Order.id == order_id)
    )
    order = result.scalar_one_or_none()
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Заказ не найден")

    if order.status != OrderStatus.OPEN:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Отклик возможен только на открытый заказ",
        )

    if order.client.user_id == expert.user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Нельзя откликнуться на свой заказ",
        )

    existing = await db.execute(
        select(Response).where(
            Response.order_id == order_id,
            Response.expert_id == expert.id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Вы уже откликались на этот заказ",
        )

    # Блокировка строки эксперта для атомарного списания баланса
    locked = await db.execute(
        select(Expert).where(Expert.id == expert.id).with_for_update()
    )
    expert_locked = locked.scalar_one()

    if Decimal(str(expert_locked.balance)) < RESPONSE_FEE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Недостаточно средств. Нужно минимум {RESPONSE_FEE} ₽",
        )

    expert_locked.balance = Decimal(str(expert_locked.balance)) - RESPONSE_FEE

    fee_transaction = Transaction(
        expert_id=expert_locked.id,
        type=TransactionType.RESPONSE_FEE,
        amount=RESPONSE_FEE,
        description=f"Плата за отклик на заказ #{order_id}",
    )
    db.add(fee_transaction)

    response = Response(
        order_id=order_id,
        expert_id=expert_locked.id,
        message=payload.message,
        cost=RESPONSE_FEE,
        status=ResponseStatus.PENDING,
    )
    db.add(response)

    try:
        await db.commit()
        await db.refresh(response)
    except Exception:
        await db.rollback()
        raise

    return ResponseResponse.model_validate(response)


@router.get("/orders/{order_id}/responses", response_model=list[ResponseWithExpertResponse])
async def list_order_responses(
    order_id: int,
    client: Client = Depends(get_current_client),
    db: AsyncSession = Depends(get_db),
) -> list[ResponseWithExpertResponse]:
    """Все отклики на заказ (только владелец заказа)."""
    order_result = await db.execute(
        select(Order).where(Order.id == order_id, Order.client_id == client.id)
    )
    if order_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Заказ не найден")

    result = await db.execute(
        select(Response)
        .options(selectinload(Response.expert))
        .where(Response.order_id == order_id)
        .order_by(Response.created_at.desc())
    )
    responses = result.scalars().all()

    return [
        ResponseWithExpertResponse(
            id=r.id,
            order_id=r.order_id,
            expert_id=r.expert_id,
            message=r.message,
            cost=r.cost,
            status=r.status,
            created_at=r.created_at,
            expert=_expert_brief(r.expert),
        )
        for r in responses
    ]


@router.put("/responses/{response_id}/accept", response_model=ResponseResponse)
async def accept_response(
    response_id: int,
    client: Client = Depends(get_current_client),
    db: AsyncSession = Depends(get_db),
) -> ResponseResponse:
    """Принять отклик: заказ → in_progress, остальные отклики → rejected."""
    result = await db.execute(
        select(Response)
        .options(selectinload(Response.order))
        .where(Response.id == response_id)
    )
    response = result.scalar_one_or_none()
    if response is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Отклик не найден")

    if response.order.client_id != client.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Нет доступа")

    if response.status != ResponseStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Отклик уже обработан",
        )

    response.status = ResponseStatus.ACCEPTED
    response.order.status = OrderStatus.IN_PROGRESS

    others = await db.execute(
        select(Response).where(
            Response.order_id == response.order_id,
            Response.id != response.id,
            Response.status == ResponseStatus.PENDING,
        )
    )
    for other in others.scalars().all():
        other.status = ResponseStatus.REJECTED

    await db.commit()
    await db.refresh(response)
    return ResponseResponse.model_validate(response)


@router.put("/responses/{response_id}/reject", response_model=ResponseResponse)
async def reject_response(
    response_id: int,
    client: Client = Depends(get_current_client),
    db: AsyncSession = Depends(get_db),
) -> ResponseResponse:
    """Отклонить отклик."""
    result = await db.execute(
        select(Response)
        .options(selectinload(Response.order))
        .where(Response.id == response_id)
    )
    response = result.scalar_one_or_none()
    if response is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Отклик не найден")

    if response.order.client_id != client.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Нет доступа")

    if response.status != ResponseStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Отклик уже обработан",
        )

    response.status = ResponseStatus.REJECTED
    await db.commit()
    await db.refresh(response)
    return ResponseResponse.model_validate(response)


@router.get("/expert/responses", response_model=list[ExpertResponseHistoryItem])
async def list_expert_responses(
    expert: Expert = Depends(get_current_expert),
    db: AsyncSession = Depends(get_db),
) -> list[ExpertResponseHistoryItem]:
    """История откликов текущего эксперта."""
    result = await db.execute(
        select(Response)
        .options(selectinload(Response.order))
        .where(Response.expert_id == expert.id)
        .order_by(Response.created_at.desc())
    )
    responses = result.scalars().all()

    return [
        ExpertResponseHistoryItem(
            id=r.id,
            order_id=r.order_id,
            expert_id=r.expert_id,
            message=r.message,
            cost=r.cost,
            status=r.status,
            created_at=r.created_at,
            order=OrderBrief(
                id=r.order.id,
                title=r.order.title,
                status=r.order.status,
                category=r.order.category,
            ),
        )
        for r in responses
    ]
