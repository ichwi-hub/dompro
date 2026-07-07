"""Лента заказов для Expert Workspace."""

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.database import get_db
from core.dependencies import get_current_expert
from models.enums import OrderStatus, ResponseStatus
from models.expert import Expert
from models.order import Order
from models.response import Response
from schemas.feed import ExpertFeedItem, ExpertFeedResponse

router = APIRouter(prefix="/expert", tags=["Лента эксперта"])


@router.get("/feed", response_model=ExpertFeedResponse)
async def expert_feed(
    expert: Expert = Depends(get_current_expert),
    db: AsyncSession = Depends(get_db),
) -> ExpertFeedResponse:
    """Новые открытые заказы и активная работа эксперта."""
    since = datetime.now(UTC) - timedelta(days=7)

    open_orders = await db.execute(
        select(Order)
        .where(
            Order.status == OrderStatus.OPEN,
            Order.created_at >= since,
            ~Order.id.in_(
                select(Response.order_id).where(Response.expert_id == expert.id)
            ),
        )
        .order_by(Order.created_at.desc())
        .limit(20)
    )

    active_orders = await db.execute(
        select(Order)
        .join(Response, Response.order_id == Order.id)
        .where(
            Response.expert_id == expert.id,
            Response.status == ResponseStatus.ACCEPTED,
        )
        .options(selectinload(Order.responses))
        .order_by(Order.created_at.desc())
        .limit(20)
    )

    pending_orders = await db.execute(
        select(Order)
        .join(Response, Response.order_id == Order.id)
        .where(
            Response.expert_id == expert.id,
            Response.status == ResponseStatus.PENDING,
            Order.status == OrderStatus.OPEN,
        )
        .options(selectinload(Order.responses))
        .order_by(Order.created_at.desc())
        .limit(20)
    )

    seen: set[int] = set()
    items: list[ExpertFeedItem] = []

    def append_order(order: Order, response: Response | None) -> None:
        if order.id in seen:
            return
        seen.add(order.id)
        items.append(
            ExpertFeedItem(
                order_id=order.id,
                title=order.title,
                description=order.description,
                budget=order.budget,
                deadline=order.deadline,
                status=order.status,
                has_response=response is not None,
                response_status=response.status if response else None,
            )
        )

    for order in active_orders.scalars().all():
        my_response = next(
            (r for r in order.responses if r.expert_id == expert.id),
            None,
        )
        append_order(order, my_response)

    for order in pending_orders.scalars().all():
        my_response = next(
            (r for r in order.responses if r.expert_id == expert.id),
            None,
        )
        append_order(order, my_response)

    for order in open_orders.scalars().all():
        append_order(order, None)

    items.sort(key=lambda x: x.order_id, reverse=True)
    items = items[:20]

    return ExpertFeedResponse(items=items, total=len(items))
