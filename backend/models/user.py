from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import BigInteger, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base
from models.enums import UserRole, VerificationStatus, pg_enum

if TYPE_CHECKING:
    from models.client import Client
    from models.expert import Expert


class User(Base):
    """Пользователь платформы (эксперт, заказчик или администратор)."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    phone: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        pg_enum(UserRole, "user_role"),
        nullable=False,
    )
    full_name: Mapped[Optional[str]] = mapped_column(String(255))
    verification_status: Mapped[VerificationStatus] = mapped_column(
        pg_enum(VerificationStatus, "verification_status"),
        nullable=False,
        default=VerificationStatus.UNVERIFIED,
    )
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

    expert: Mapped[Optional["Expert"]] = relationship(
        back_populates="user",
        foreign_keys="[Expert.user_id]",
        uselist=False,
        cascade="all, delete-orphan",
    )
    client: Mapped[Optional["Client"]] = relationship(
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )

    @property
    def is_verified_expert(self) -> bool:
        """Эксперт может откликаться на заказы только после верификации."""
        return (
            self.role == UserRole.EXPERT
            and self.verification_status == VerificationStatus.VERIFIED
        )
