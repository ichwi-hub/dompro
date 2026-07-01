from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, Numeric, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base
from models.enums import ResponseStatus, pg_enum

if TYPE_CHECKING:
    from models.expert import Expert
    from models.order import Order


class Response(Base):
    """Отклик эксперта на заказ (при создании списывается response_fee)."""

    __tablename__ = "responses"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
    )
    expert_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("experts.id", ondelete="CASCADE"),
        nullable=False,
    )
    message: Mapped[Optional[str]] = mapped_column(Text)
    cost: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    status: Mapped[ResponseStatus] = mapped_column(
        pg_enum(ResponseStatus, "response_status"),
        nullable=False,
        default=ResponseStatus.PENDING,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    order: Mapped["Order"] = relationship(back_populates="responses")
    expert: Mapped["Expert"] = relationship(back_populates="responses")
