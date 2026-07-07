"""API раздела "Мои клиенты" для workspace эксперта."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.dependencies import get_current_expert
from models.client import Client
from models.enums import ResponseStatus
from models.expert import Expert
from models.order import Order
from models.response import Response
from schemas.client import (
    ExpertClientDetail,
    ExpertClientListItem,
    ExpertClientListResponse,
)

router = APIRouter(prefix="/expert/clients", tags=["Клиенты эксперта"])


def _normalize_name(full_name: str | None, company_name: str | None, client_id: int) -> str:
    if full_name:
        return full_name
    if company_name:
        return company_name
    return f"Клиент #{client_id}"


@router.get("", response_model=ExpertClientListResponse)
async def list_expert_clients(
    expert: Expert = Depends(get_current_expert),
    db: AsyncSession = Depends(get_db),
) -> ExpertClientListResponse:
    """Список клиентов, с которыми есть принятые отклики эксперта."""
    query = (
        select(
            Client.id.label("client_id"),
            User.full_name.label("full_name"),
            Client.company_name.label("company_name"),
            func.count(func.distinct(Order.id)).label("accepted_orders_count"),
            func.max(Order.created_at).label("last_activity_at"),
        )
        .join(User, User.id == Client.user_id)
        .join(Order, Order.client_id == Client.id)
        .join(Response, Response.order_id == Order.id)
        .where(
            Response.expert_id == expert.id,
            Response.status == ResponseStatus.ACCEPTED,
        )
        .group_by(Client.id, User.full_name, Client.company_name)
        .order_by(func.max(Order.created_at).desc(), Client.id.desc())
    )
    rows = (await db.execute(query)).all()
    if not rows:
        return ExpertClientListResponse(items=[])

    latest_titles_query = (
        select(
            Client.id.label("client_id"),
            Order.title.label("order_title"),
            Order.created_at.label("created_at"),
            func.row_number()
            .over(partition_by=Client.id, order_by=Order.created_at.desc())
            .label("row_num"),
        )
        .join(Order, Order.client_id == Client.id)
        .join(Response, Response.order_id == Order.id)
        .where(
            Response.expert_id == expert.id,
            Response.status == ResponseStatus.ACCEPTED,
        )
    ).subquery()
    latest_rows = await db.execute(
        select(
            latest_titles_query.c.client_id,
            latest_titles_query.c.order_title,
        ).where(latest_titles_query.c.row_num == 1)
    )
    latest_titles = {row.client_id: row.order_title for row in latest_rows}

    return ExpertClientListResponse(
        items=[
            ExpertClientListItem(
                id=row.client_id,
                full_name=_normalize_name(row.full_name, row.company_name, row.client_id),
                company_name=row.company_name,
                accepted_orders_count=row.accepted_orders_count,
                last_order_title=latest_titles.get(row.client_id),
                last_activity_at=row.last_activity_at,
            )
            for row in rows
        ]
    )


@router.get("/{client_id}", response_model=ExpertClientDetail)
async def get_expert_client_detail(
    client_id: int,
    expert: Expert = Depends(get_current_expert),
    db: AsyncSession = Depends(get_db),
) -> ExpertClientDetail:
    """Карточка клиента для эксперта по accepted-откликам."""
    base_query = (
        select(
            Client.id.label("client_id"),
            User.full_name.label("full_name"),
            Client.company_name.label("company_name"),
            func.count(func.distinct(Order.id)).label("accepted_orders_count"),
            func.count(Response.id).label("accepted_responses_count"),
            func.max(Order.created_at).label("last_activity_at"),
        )
        .join(User, User.id == Client.user_id)
        .join(Order, Order.client_id == Client.id)
        .join(Response, Response.order_id == Order.id)
        .where(
            Client.id == client_id,
            Response.expert_id == expert.id,
            Response.status == ResponseStatus.ACCEPTED,
        )
        .group_by(Client.id, User.full_name, Client.company_name)
    )
    row = (await db.execute(base_query)).one_or_none()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Клиент не найден")

    latest_order_query = (
        select(Order.title)
        .join(Response, Response.order_id == Order.id)
        .where(
            Order.client_id == client_id,
            Response.expert_id == expert.id,
            Response.status == ResponseStatus.ACCEPTED,
        )
        .order_by(Order.created_at.desc())
        .limit(1)
    )
    latest_order_title = await db.scalar(latest_order_query)

    return ExpertClientDetail(
        id=row.client_id,
        full_name=_normalize_name(row.full_name, row.company_name, row.client_id),
        company_name=row.company_name,
        accepted_orders_count=row.accepted_orders_count,
        accepted_responses_count=row.accepted_responses_count,
        last_order_title=latest_order_title,
        last_activity_at=row.last_activity_at,
    )
