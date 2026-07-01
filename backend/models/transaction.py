from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, Numeric, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base
from models.enums import TransactionType, pg_enum

if TYPE_CHECKING:
    from models.expert import Expert


class Transaction(Base):
    """Операция с внутренним балансом эксперта (пополнение или плата за отклик)."""

    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    expert_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("experts.id", ondelete="CASCADE"),
        nullable=False,
    )
    type: Mapped[TransactionType] = mapped_column(
        pg_enum(TransactionType, "transaction_type"),
        nullable=False,
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    expert: Mapped["Expert"] = relationship(back_populates="transactions")
