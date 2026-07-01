from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base

if TYPE_CHECKING:
    from models.contract import Contract
    from models.response import Response
    from models.transaction import Transaction
    from models.user import User
    from models.verification import ExpertVerification


class Expert(Base):
    """Профиль эксперта: данные, баланс и верификация."""

    __tablename__ = "experts"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    category: Mapped[Optional[str]] = mapped_column(String(128), default="")
    full_name: Mapped[Optional[str]] = mapped_column(String(255))
    photo_url: Mapped[Optional[str]] = mapped_column(Text)
    experience_years: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    specialization: Mapped[Optional[str]] = mapped_column(String(255))
    description: Mapped[Optional[str]] = mapped_column(Text)
    rating: Mapped[Decimal] = mapped_column(
        Numeric(3, 2),
        nullable=False,
        default=Decimal("0.00"),
    )
    balance: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=Decimal("0.00"),
    )
    inn: Mapped[Optional[str]] = mapped_column(String(12))
    diploma_url: Mapped[Optional[str]] = mapped_column(Text)
    self_employment_url: Mapped[Optional[str]] = mapped_column(Text)
    bar_association_url: Mapped[Optional[str]] = mapped_column(Text)
    verified_by: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="SET NULL"),
    )
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    user: Mapped["User"] = relationship(
        back_populates="expert",
        foreign_keys=[user_id],
    )
    verifier: Mapped[Optional["User"]] = relationship(foreign_keys=[verified_by])
    responses: Mapped[list["Response"]] = relationship(back_populates="expert")
    transactions: Mapped[list["Transaction"]] = relationship(back_populates="expert")
    contracts: Mapped[list["Contract"]] = relationship(back_populates="expert")
    verifications: Mapped[list["ExpertVerification"]] = relationship(
        back_populates="expert",
        cascade="all, delete-orphan",
    )

    @property
    def is_profile_complete(self) -> bool:
        """Профиль заполнен (этап 2) — обязателен перед верификацией."""
        return bool(
            self.full_name
            and self.experience_years is not None
            and self.specialization
            and self.description
        )

    @property
    def is_visible_in_catalog(self) -> bool:
        """Неверифицированные эксперты скрыты из каталога."""
        return self.user.is_verified_expert if self.user else False
