import enum

from sqlalchemy import Enum as SAEnum


def pg_enum(enum_cls: type[enum.Enum], name: str) -> SAEnum:
    """PostgreSQL ENUM с lowercase-значениями из str Enum."""
    return SAEnum(
        enum_cls,
        name=name,
        create_constraint=False,
        native_enum=True,
        values_callable=lambda items: [item.value for item in items],
    )


class UserRole(str, enum.Enum):
    """Роль пользователя в системе."""

    CLIENT = "client"
    EXPERT = "expert"
    ADMIN = "admin"


class VerificationStatus(str, enum.Enum):
    """Статус верификации пользователя-эксперта."""

    UNVERIFIED = "unverified"
    VERIFICATION_PENDING = "verification_pending"
    VERIFIED = "verified"
    REJECTED = "rejected"


class ExpertVerificationStatus(str, enum.Enum):
    """Статус заявки на верификацию."""

    PENDING = "pending"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"


class OrderStatus(str, enum.Enum):
    """Статус заказа клиента."""

    OPEN = "open"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ResponseStatus(str, enum.Enum):
    """Статус отклика эксперта."""

    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class TransactionType(str, enum.Enum):
    """Тип внутренней транзакции баланса эксперта."""

    DEPOSIT = "deposit"
    RESPONSE_FEE = "response_fee"
