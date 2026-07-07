"""API договоров: генерация PDF, просмотр, скачивание."""

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.database import get_db
from core.dependencies import get_current_client, get_current_expert, get_current_user
from models.client import Client
from models.contract import Contract
from models.enums import OrderStatus, ResponseStatus, UserRole
from models.expert import Expert
from models.order import Order
from models.response import Response
from models.user import User
from schemas.contract import ContractResponse, ExpertContractListItem, ExpertContractListResponse
from services.contract_service import generate_contract, resolve_contract_file

router = APIRouter(tags=["Договоры"])


def _client_display_name(client: Client) -> str:
    if client.company_name:
        return client.company_name
    if client.user and client.user.full_name:
        return client.user.full_name
    return f"Клиент #{client.id}"


async def _get_order_participants(
    db: AsyncSession,
    order_id: int,
) -> tuple[Order, Response | None]:
    result = await db.execute(
        select(Order)
        .options(selectinload(Order.client).selectinload(Client.user))
        .where(Order.id == order_id)
    )
    order = result.scalar_one_or_none()
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Заказ не найден")

    accepted = await db.execute(
        select(Response).where(
            Response.order_id == order_id,
            Response.status == ResponseStatus.ACCEPTED,
        )
    )
    return order, accepted.scalar_one_or_none()


async def _ensure_order_contract_access(
    user: User,
    order: Order,
    accepted: Response | None,
    expert: Expert | None = None,
) -> None:
    if user.role == UserRole.CLIENT:
        if order.client.user_id != user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Нет доступа")
        return

    if user.role == UserRole.EXPERT and expert is not None:
        if accepted is None or accepted.expert_id != expert.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Нет доступа")
        return

    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Нет доступа")


async def _get_contract_for_user(
    contract_id: int,
    user: User,
    db: AsyncSession,
    expert: Expert | None = None,
) -> Contract:
    result = await db.execute(
        select(Contract)
        .options(
            selectinload(Contract.order),
            selectinload(Contract.client).selectinload(Client.user),
        )
        .where(Contract.id == contract_id)
    )
    contract = result.scalar_one_or_none()
    if contract is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Договор не найден")

    if user.role == UserRole.CLIENT:
        if contract.client.user_id != user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Нет доступа")
        return contract

    if user.role == UserRole.EXPERT and expert is not None:
        if contract.expert_id != expert.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Нет доступа")
        return contract

    if user.role == UserRole.ADMIN:
        return contract

    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Нет доступа")


@router.post(
    "/orders/{order_id}/contract",
    response_model=ContractResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_order_contract(
    order_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ContractResponse:
    """Сгенерировать договор по заказу в работе (эксперт или заказчик)."""
    order, accepted = await _get_order_participants(db, order_id)

    if order.status != OrderStatus.IN_PROGRESS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Договор доступен только для заказа в работе",
        )
    if accepted is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Нет принятого отклика по заказу",
        )

    expert: Expert | None = None
    if user.role == UserRole.EXPERT:
        expert_result = await db.execute(select(Expert).where(Expert.user_id == user.id))
        expert = expert_result.scalar_one_or_none()
        if expert is None:
            raise HTTPException(status_code=404, detail="Профиль эксперта не найден")
    elif user.role != UserRole.CLIENT:
        raise HTTPException(status_code=403, detail="Доступ только для эксперта или заказчика")

    await _ensure_order_contract_access(user, order, accepted, expert)

    existing = await db.execute(select(Contract).where(Contract.order_id == order_id))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Договор по заказу уже создан")

    try:
        contract = await generate_contract(
            db,
            order_id=order_id,
            expert_id=accepted.expert_id,
            client_id=order.client_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return ContractResponse.model_validate(contract)


@router.get("/contracts/{contract_id}", response_model=ContractResponse)
async def get_contract(
    contract_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ContractResponse:
    """Метаданные договора."""
    expert = None
    if user.role == UserRole.EXPERT:
        result = await db.execute(select(Expert).where(Expert.user_id == user.id))
        expert = result.scalar_one_or_none()

    contract = await _get_contract_for_user(contract_id, user, db, expert)
    return ContractResponse.model_validate(contract)


@router.get("/contracts/{contract_id}/download")
async def download_contract(
    contract_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FileResponse:
    """Скачать PDF договора."""
    expert = None
    if user.role == UserRole.EXPERT:
        result = await db.execute(select(Expert).where(Expert.user_id == user.id))
        expert = result.scalar_one_or_none()

    contract = await _get_contract_for_user(contract_id, user, db, expert)
    try:
        path = resolve_contract_file(contract)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return FileResponse(
        Path(path),
        media_type="application/pdf",
        filename=f"contract_{contract.id}.pdf",
    )


@router.get("/expert/contracts", response_model=ExpertContractListResponse)
async def list_expert_contracts(
    expert: Expert = Depends(get_current_expert),
    db: AsyncSession = Depends(get_db),
) -> ExpertContractListResponse:
    """Список договоров текущего эксперта."""
    result = await db.execute(
        select(Contract)
        .options(
            selectinload(Contract.order),
            selectinload(Contract.client).selectinload(Client.user),
        )
        .where(Contract.expert_id == expert.id)
        .order_by(Contract.created_at.desc())
    )
    contracts = result.scalars().all()

    items = [
        ExpertContractListItem(
            id=c.id,
            order_id=c.order_id,
            order_title=c.order.title,
            client_name=_client_display_name(c.client),
            status=c.status,
            created_at=c.created_at,
            pdf_path=c.pdf_path,
        )
        for c in contracts
    ]
    return ExpertContractListResponse(items=items, total=len(items))


@router.get("/orders/{order_id}/contract", response_model=ContractResponse | None)
async def get_order_contract(
    order_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ContractResponse | None:
    """Проверить, есть ли договор по заказу."""
    order, accepted = await _get_order_participants(db, order_id)
    expert = None
    if user.role == UserRole.EXPERT:
        row = await db.execute(select(Expert).where(Expert.user_id == user.id))
        expert = row.scalar_one_or_none()
    await _ensure_order_contract_access(user, order, accepted, expert)

    result = await db.execute(select(Contract).where(Contract.order_id == order_id))
    contract = result.scalar_one_or_none()
    if contract is None:
        return None
    return ContractResponse.model_validate(contract)
