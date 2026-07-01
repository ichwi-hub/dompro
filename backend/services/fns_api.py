import re
from dataclasses import dataclass


@dataclass
class InnCheckResult:
    """Результат проверки ИНН."""

    valid: bool
    message: str


def _inn_checksum(inn: str, coefficients: list[int]) -> bool:
    total = sum(int(d) * c for d, c in zip(inn[:-1], coefficients, strict=False))
    check = total % 11 % 10
    return check == int(inn[-1])


def check_inn(inn: str) -> InnCheckResult:
    """Проверка ИНН (заглушка ФНС: формат + контрольная сумма).

    В будущем здесь будет запрос к API ФНС.
    """
    cleaned = re.sub(r"\D", "", inn)
    if len(cleaned) not in (10, 12):
        return InnCheckResult(False, "ИНН должен содержать 10 или 12 цифр")

    if not cleaned.isdigit():
        return InnCheckResult(False, "ИНН должен состоять только из цифр")

    if len(cleaned) == 10:
        ok = _inn_checksum(cleaned, [2, 4, 10, 3, 5, 9, 4, 6, 8])
    else:
        ok11 = _inn_checksum(cleaned, [7, 2, 4, 10, 3, 5, 9, 4, 6, 8])
        ok12 = _inn_checksum(cleaned, [3, 7, 2, 4, 10, 3, 5, 9, 4, 6, 8])
        ok = ok11 and ok12

    if not ok:
        return InnCheckResult(False, "Некорректная контрольная сумма ИНН")

    return InnCheckResult(True, "ИНН прошёл автоматическую проверку (заглушка ФНС)")


def notify_admin_new_verification(expert_id: int, verification_id: int) -> None:
    """Уведомление администратора о новой заявке (заглушка)."""
    print(
        f"[ADMIN NOTIFY] Новая заявка на верификацию: "
        f"expert_id={expert_id}, verification_id={verification_id}"
    )
