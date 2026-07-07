"""Генерация PDF-договоров."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from io import BytesIO
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from xhtml2pdf import pisa

from core.config import PROJECT_ROOT, settings
from models.client import Client
from models.contract import Contract
from models.enums import ContractStatus, OrderStatus, ResponseStatus
from models.expert import Expert
from models.order import Order
from models.response import Response

TEMPLATES_DIR = PROJECT_ROOT / "backend" / "templates"


def _format_price(value: Decimal | None) -> str:
    if value is None:
        return "не указана"
    return f"{value:,.2f}".replace(",", " ")


def _format_deadline(value: date | None) -> str:
    if value is None:
        return "по согласованию Сторон"
    return value.strftime("%d.%m.%Y")


def render_contract_html(
    *,
    expert_name: str,
    client_name: str,
    order_description: str,
    price: Decimal | None,
    deadline: date | None,
    contract_date: datetime | None = None,
) -> str:
    env = Environment(
        loader=FileSystemLoader(TEMPLATES_DIR),
        autoescape=select_autoescape(["html"]),
    )
    template = env.get_template("contract.html")
    when = contract_date or datetime.now(UTC)
    return template.render(
        expert_name=expert_name,
        client_name=client_name,
        order_description=order_description or "Услуги по заказу на платформе DomPro",
        price=_format_price(price),
        deadline=_format_deadline(deadline),
        date=when.strftime("%d.%m.%Y"),
    )


def html_to_pdf_bytes(html: str) -> bytes:
    buffer = BytesIO()
    result = pisa.CreatePDF(html, dest=buffer, encoding="utf-8")
    if result.err:
        raise RuntimeError("Ошибка генерации PDF")
    return buffer.getvalue()


async def get_accepted_response(
    db: AsyncSession,
    order_id: int,
) -> Response | None:
    result = await db.execute(
        select(Response)
        .options(selectinload(Response.expert).selectinload(Expert.user))
        .where(
            Response.order_id == order_id,
            Response.status == ResponseStatus.ACCEPTED,
        )
    )
    return result.scalar_one_or_none()


async def generate_contract(
    db: AsyncSession,
    *,
    order_id: int,
    expert_id: int,
    client_id: int,
) -> Contract:
    """Создать запись договора и сохранить PDF в локальное хранилище."""
    order_result = await db.execute(
        select(Order)
        .options(
            selectinload(Order.client).selectinload(Client.user),
            selectinload(Order.contracts),
        )
        .where(Order.id == order_id)
    )
    order = order_result.scalar_one()

    if order.status != OrderStatus.IN_PROGRESS:
        raise ValueError("Договор можно создать только для заказа в работе")

    if order.client_id != client_id:
        raise ValueError("Заказчик не совпадает с заказом")

    accepted = await get_accepted_response(db, order_id)
    if accepted is None or accepted.expert_id != expert_id:
        raise ValueError("Нет принятого отклика эксперта по этому заказу")

    if order.contracts:
        raise ValueError("Договор по этому заказу уже существует")

    expert_result = await db.execute(
        select(Expert)
        .options(selectinload(Expert.user))
        .where(Expert.id == expert_id)
    )
    expert = expert_result.scalar_one()

    client = order.client
    expert_name = expert.full_name or (expert.user.full_name if expert.user else f"Эксперт #{expert.id}")
    client_name = client.company_name or (client.user.full_name if client.user else f"Клиент #{client.id}")

    price = accepted.cost if accepted.cost else order.budget

    contract = Contract(
        order_id=order_id,
        expert_id=expert_id,
        client_id=client_id,
        pdf_path="",
        status=ContractStatus.DRAFT,
    )
    db.add(contract)
    await db.flush()

    html = render_contract_html(
        expert_name=expert_name,
        client_name=client_name,
        order_description=order.description or order.title,
        price=Decimal(str(price)) if price is not None else None,
        deadline=order.deadline,
    )
    pdf_bytes = html_to_pdf_bytes(html)

    storage_key = f"contracts/{contract.id}.pdf"
    full_path = settings.local_storage_root / storage_key
    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_bytes(pdf_bytes)

    contract.pdf_path = storage_key
    contract.updated_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(contract)
    return contract


def resolve_contract_file(contract: Contract) -> Path:
    path = settings.local_storage_root / contract.pdf_path.lstrip("/")
    if not path.is_file():
        raise FileNotFoundError("PDF договора не найден")
    return path
