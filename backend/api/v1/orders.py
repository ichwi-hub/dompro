"""API заказов: создание клиентом, лента для экспертов, смена статуса."""

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.database import get_db
from core.dependencies import get_current_client, get_current_user
from models.client import Client
from models.enums import OrderStatus, ResponseStatus, UserRole
from models.expert import Expert
from models.order import Order
from models.response import Response
from models.user import User
from schemas.order import OrderCreate, OrderListResponse, OrderResponse, OrderStatusUpdate

router = APIRouter(tags=["Заказы"])

ALLOWED_STATUS_UPDATES = {
    OrderStatus.IN_PROGRESS,
    OrderStatus.COMPLETED,
    OrderStatus.CANCELLED,
}


def _client_display_name(client: Client) -> str:
    """Отображаемое имя заказчика без контактных данных."""
    if client.company_name:
        return client.company_name
    if client.user and client.user.full_name:
        return client.user.full_name
    return "Заказчик"


def _order_to_response(order: Order, *, show_client_name: bool = False) -> OrderResponse:
    """Сборка ответа с опциональным именем заказчика (без email/телефона)."""
    display_name = _client_display_name(order.client) if show_client_name and order.client else None
    return OrderResponse(
        id=order.id,
        client_id=order.client_id,
        title=order.title,
        description=order.description,
        category=order.category,
        budget=order.budget,
        deadline=order.deadline,
        status=order.status,
        created_at=order.created_at,
        client_display_name=display_name,
    )


@router.post("", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order(
    payload: OrderCreate,
    client: Client = Depends(get_current_client),
    db: AsyncSession = Depends(get_db),
) -> OrderResponse:
    """Создать заказ (только заказчик). Статус по умолчанию — open."""
    order = Order(
        client_id=client.id,
        title=payload.title,
        description=payload.description,
        category=payload.category,
        budget=payload.budget,
        deadline=payload.deadline,
        status=OrderStatus.OPEN,
    )
    db.add(order)
    await db.commit()
    await db.refresh(order)

    result = await db.execute(
        select(Order)
        .options(selectinload(Order.client).selectinload(Client.user))
        .where(Order.id == order.id)
    )
    order = result.scalar_one()
    return _order_to_response(order)


@router.get("", response_model=OrderListResponse)
async def list_orders(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    category: str | None = Query(None),
    budget_min: Decimal | None = Query(None, ge=0),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> OrderListResponse:
    """Список заказов.

    Клиент видит только свои заказы (все статусы).
    Эксперт видит только открытые заказы (open) без контактов заказчика.
    """
    query = select(Order).options(selectinload(Order.client).selectinload(Client.user))

    if user.role == UserRole.CLIENT:
        client_result = await db.execute(select(Client).where(Client.user_id == user.id))
        client = client_result.scalar_one_or_none()
        if client is None:
            raise HTTPException(status_code=404, detail="Профиль заказчика не найден")
        query = query.where(Order.client_id == client.id)
        show_client_name = False
    elif user.role == UserRole.EXPERT:
        query = query.where(Order.status == OrderStatus.OPEN)
        show_client_name = True
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ только для заказчиков и экспертов",
        )

    if category:
        query = query.where(Order.category == category)
    if budget_min is not None:
        query = query.where(Order.budget.is_not(None), Order.budget >= budget_min)

    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query) or 0

    offset = (page - 1) * limit
    result = await db.execute(
        query.order_by(Order.created_at.desc()).offset(offset).limit(limit)
    )
    orders = result.scalars().all()

    return OrderListResponse(
        items=[_order_to_response(o, show_client_name=show_client_name) for o in orders],
        total=total,
        page=page,
        limit=limit,
    )


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> OrderResponse:
    """Детали заказа.

    Клиент — только свой заказ. Эксперт — только открытые заказы.
    """
    result = await db.execute(
        select(Order)
        .options(selectinload(Order.client).selectinload(Client.user))
        .where(Order.id == order_id)
    )
    order = result.scalar_one_or_none()
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Заказ не найден")

    if user.role == UserRole.CLIENT:
        if order.client.user_id != user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Нет доступа к заказу")
        return _order_to_response(order)

    if user.role == UserRole.EXPERT:
        expert_result = await db.execute(select(Expert).where(Expert.user_id == user.id))
        expert = expert_result.scalar_one_or_none()
        if expert is None:
            raise HTTPException(status_code=404, detail="Профиль эксперта не найден")

        if order.status == OrderStatus.OPEN:
            return _order_to_response(order, show_client_name=True)

        response_result = await db.execute(
            select(Response).where(
                Response.order_id == order_id,
                Response.expert_id == expert.id,
            )
        )
        my_response = response_result.scalar_one_or_none()
        if my_response and order.status == OrderStatus.IN_PROGRESS:
            return _order_to_response(order, show_client_name=True)

        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Заказ недоступен")

    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Нет доступа")


@router.put("/{order_id}/status", response_model=OrderResponse)
async def update_order_status(
    order_id: int,
    payload: OrderStatusUpdate,
    client: Client = Depends(get_current_client),
    db: AsyncSession = Depends(get_db),
) -> OrderResponse:
    """Обновить статус заказа (только владелец-заказчик)."""
    if payload.status not in ALLOWED_STATUS_UPDATES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Допустимые статусы: in_progress, completed, cancelled",
        )

    result = await db.execute(
        select(Order)
        .options(selectinload(Order.client).selectinload(Client.user))
        .where(Order.id == order_id, Order.client_id == client.id)
    )
    order = result.scalar_one_or_none()
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Заказ не найден")

    order.status = payload.status
    await db.commit()
    await db.refresh(order)
    return _order_to_response(order)
