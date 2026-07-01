from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base
from models.enums import ExpertVerificationStatus, pg_enum

if TYPE_CHECKING:
    from models.expert import Expert
    from models.user import User


class ExpertVerification(Base):
    """Заявка эксперта на верификацию квалификации."""

    __tablename__ = "expert_verifications"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    expert_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("experts.id", ondelete="CASCADE"),
        nullable=False,
    )
    inn: Mapped[str] = mapped_column(String(12), nullable=False)
    diploma_url: Mapped[str] = mapped_column(Text, nullable=False)
    self_employment_url: Mapped[str] = mapped_column(Text, nullable=False)
    bar_association_url: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[ExpertVerificationStatus] = mapped_column(
        pg_enum(ExpertVerificationStatus, "expert_verification_status"),
        nullable=False,
        default=ExpertVerificationStatus.PENDING,
    )
    reviewed_by: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="SET NULL"),
    )
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
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

    expert: Mapped["Expert"] = relationship(back_populates="verifications")
    reviewer: Mapped[Optional["User"]] = relationship(foreign_keys=[reviewed_by])
