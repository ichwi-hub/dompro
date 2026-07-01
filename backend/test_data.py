"""Создание тестовых пользователей для проверки MVP DomPro.

Запуск:
    cd backend
    python test_data.py

Создаёт 6 пользователей: админ, 2 верифицированных эксперта, 1 неверифицированный,
2 клиента. Пропускает уже существующих (по email).
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import AsyncSessionLocal
from core.security import hash_password
from models.client import Client
from models.enums import UserRole, VerificationStatus
from models.expert import Expert
from models.user import User


@dataclass(frozen=True)
class TestUserSpec:
    """Описание тестового пользователя для вывода в консоль."""

    email: str
    phone: str
    password: str
    role: str
    label: str


# Спецификации для итогового отчёта (credentials)
TEST_USERS_REPORT: list[TestUserSpec] = [
    TestUserSpec("admin@dompro.ru", "+79000000001", "Admin12345", "admin", "Администратор"),
    TestUserSpec(
        "expert_verified@dompro.ru",
        "+79000000002",
        "Expert12345",
        "expert",
        "Верифицированный эксперт №1",
    ),
    TestUserSpec(
        "expert_verified2@dompro.ru",
        "+79000000003",
        "Expert12345",
        "expert",
        "Верифицированный эксперт №2",
    ),
    TestUserSpec(
        "expert_unverified@dompro.ru",
        "+79000000004",
        "Expert12345",
        "expert",
        "Неверифицированный эксперт",
    ),
    TestUserSpec("client1@dompro.ru", "+79000000005", "Client12345", "client", "Клиент №1"),
    TestUserSpec("client2@dompro.ru", "+79000000006", "Client12345", "client", "Клиент №2"),
]


async def get_user_by_email(session: AsyncSession, email: str) -> User | None:
    """Найти пользователя по email."""
    result = await session.execute(select(User).where(User.email == email.lower()))
    return result.scalar_one_or_none()


async def get_user_by_phone(session: AsyncSession, phone: str) -> User | None:
    """Найти пользователя по телефону."""
    result = await session.execute(select(User).where(User.phone == phone))
    return result.scalar_one_or_none()


async def create_user_base(
    session: AsyncSession,
    *,
    email: str,
    phone: str,
    password: str,
    role: UserRole,
    full_name: str | None = None,
    verification_status: VerificationStatus = VerificationStatus.UNVERIFIED,
) -> tuple[User, bool]:
    """Создать пользователя или вернуть/обновить существующего.

    Проверяет email и phone — не создаёт дубликаты.
    Если телефон занят старым тестовым аккаунтом, обновляет его под новую спецификацию.

    Returns:
        (user, created) — created=True, если запись только что создана.
    """
    email = email.lower()
    existing = await get_user_by_email(session, email)
    if existing:
        print(f"  [SKIP] Уже существует: {email}")
        # Обновляем поля на случай изменения спецификации
        existing.phone = phone
        existing.password_hash = hash_password(password)
        existing.role = role
        existing.full_name = full_name
        existing.verification_status = verification_status
        return existing, False

    by_phone = await get_user_by_phone(session, phone)
    if by_phone:
        print(f"  [UPDATE] Телефон {phone} занят ({by_phone.email}) -> обновляем под {email}")
        by_phone.email = email
        by_phone.password_hash = hash_password(password)
        by_phone.role = role
        by_phone.full_name = full_name
        by_phone.verification_status = verification_status
        return by_phone, False

    user = User(
        email=email,
        phone=phone,
        password_hash=hash_password(password),
        role=role,
        full_name=full_name,
        verification_status=verification_status,
    )
    session.add(user)
    await session.flush()
    print(f"  [OK] Создан пользователь: {email} ({role.value})")
    return user, True


async def create_expert_profile(
    session: AsyncSession,
    user: User,
    *,
    full_name: str,
    experience_years: int,
    specialization: str,
    description: str,
    balance: Decimal = Decimal("0.00"),
    verified: bool = False,
) -> Expert:
    """Создать или обновить профиль эксперта."""
    result = await session.execute(select(Expert).where(Expert.user_id == user.id))
    expert = result.scalar_one_or_none()
    if expert is None:
        expert = Expert(user_id=user.id)
        session.add(expert)
        await session.flush()

    expert.full_name = full_name
    expert.experience_years = experience_years
    expert.specialization = specialization
    expert.description = description
    expert.category = specialization
    expert.balance = balance

    if verified:
        now = datetime.now(timezone.utc)
        expert.verified_at = expert.verified_at or now
        expert.rejection_reason = None
        user.verification_status = VerificationStatus.VERIFIED

    return expert


async def create_client_profile(
    session: AsyncSession,
    user: User,
    *,
    company_name: str | None = None,
) -> Client:
    """Создать или обновить профиль клиента."""
    result = await session.execute(select(Client).where(Client.user_id == user.id))
    client = result.scalar_one_or_none()
    if client is None:
        client = Client(user_id=user.id)
        session.add(client)
        await session.flush()

    client.company_name = company_name
    return client


async def seed_test_data(session: AsyncSession) -> dict[str, int]:
    """Заполнить БД тестовыми данными в одной транзакции."""
    stats = {"created": 0, "skipped": 0}

    # 1. Администратор
    admin, created = await create_user_base(
        session,
        email="admin@dompro.ru",
        phone="+79000000001",
        password="Admin12345",
        role=UserRole.ADMIN,
        full_name="Администратор DomPro",
        verification_status=VerificationStatus.VERIFIED,
    )
    stats["created" if created else "skipped"] += 1

    # 2. Верифицированный эксперт №1 (с балансом)
    expert1_user, created = await create_user_base(
        session,
        email="expert_verified@dompro.ru",
        phone="+79000000002",
        password="Expert12345",
        role=UserRole.EXPERT,
        full_name="Иван Петров",
        verification_status=VerificationStatus.VERIFIED,
    )
    await create_expert_profile(
        session,
        expert1_user,
        full_name="Иван Петров",
        experience_years=10,
        specialization="Уголовное право",
        description="Адвокат с 10-летним опытом",
        balance=Decimal("5000.00"),
        verified=True,
    )
    stats["created" if created else "skipped"] += 1

    # 3. Верифицированный эксперт №2 (с балансом)
    expert2_user, created = await create_user_base(
        session,
        email="expert_verified2@dompro.ru",
        phone="+79000000003",
        password="Expert12345",
        role=UserRole.EXPERT,
        full_name="Мария Сидорова",
        verification_status=VerificationStatus.VERIFIED,
    )
    await create_expert_profile(
        session,
        expert2_user,
        full_name="Мария Сидорова",
        experience_years=7,
        specialization="Семейное право",
        description="Специалист по разводам и алиментам",
        balance=Decimal("3000.00"),
        verified=True,
    )
    stats["created" if created else "skipped"] += 1

    # 4. Неверифицированный эксперт (профиль заполнен)
    expert3_user, created = await create_user_base(
        session,
        email="expert_unverified@dompro.ru",
        phone="+79000000004",
        password="Expert12345",
        role=UserRole.EXPERT,
        full_name="Тест Тестов",
        verification_status=VerificationStatus.UNVERIFIED,
    )
    await create_expert_profile(
        session,
        expert3_user,
        full_name="Тест Тестов",
        experience_years=3,
        specialization="Гражданское право",
        description="Тестовый эксперт без верификации",
        balance=Decimal("0.00"),
        verified=False,
    )
    stats["created" if created else "skipped"] += 1

    # 5. Клиент №1
    client1_user, created = await create_user_base(
        session,
        email="client1@dompro.ru",
        phone="+79000000005",
        password="Client12345",
        role=UserRole.CLIENT,
        full_name="Алексей Клиентов",
    )
    await create_client_profile(session, client1_user)
    stats["created" if created else "skipped"] += 1

    # 6. Клиент №2 (компания)
    client2_user, created = await create_user_base(
        session,
        email="client2@dompro.ru",
        phone="+79000000006",
        password="Client12345",
        role=UserRole.CLIENT,
        full_name='ООО "Ромашка"',
    )
    await create_client_profile(session, client2_user, company_name='ООО "Ромашка"')
    stats["created" if created else "skipped"] += 1

    return stats


def print_credentials_report() -> None:
    """Вывести список тестовых учётных записей."""
    print("\n" + "=" * 60)
    print("ТЕСТОВЫЕ УЧЁТНЫЕ ЗАПИСИ DomPro")
    print("=" * 60)
    for spec in TEST_USERS_REPORT:
        print(f"\n{spec.label}")
        print(f"  Email:    {spec.email}")
        print(f"  Phone:    {spec.phone}")
        print(f"  Password: {spec.password}")
        print(f"  Role:     {spec.role}")
    print("\n" + "=" * 60)


async def print_db_summary(session: AsyncSession) -> None:
    """Итоговая сводка по таблицам users, experts, clients."""
    users_count = await session.scalar(select(func.count()).select_from(User))
    experts_count = await session.scalar(select(func.count()).select_from(Expert))
    clients_count = await session.scalar(select(func.count()).select_from(Client))

    result = await session.execute(
        select(User.email, User.role, User.verification_status)
        .where(
            User.email.in_([spec.email for spec in TEST_USERS_REPORT])
        )
        .order_by(User.id)
    )
    rows = result.all()

    print("\nИТОГОВЫЙ ОТЧЁТ")
    print("-" * 60)
    print(f"Всего users в БД:   {users_count}")
    print(f"Всего experts в БД: {experts_count}")
    print(f"Всего clients в БД: {clients_count}")
    print(f"Тестовых аккаунтов: {len(rows)} / 6")
    print("-" * 60)
    for email, role, status in rows:
        print(f"  {email:35} {role.value:8} {status.value}")
    print("-" * 60)

    if len(rows) < 6:
        print("ВНИМАНИЕ: не все 6 тестовых пользователей найдены в БД!")
    else:
        print("Все 6 тестовых пользователей присутствуют в БД.")


async def main() -> None:
    """Точка входа: создание тестовых данных в транзакции."""
    print("Создание тестовых данных DomPro...")
    print("-" * 60)

    try:
        async with AsyncSessionLocal() as session:
            async with session.begin():
                stats = await seed_test_data(session)

            # Отдельная сессия для чтения после commit
            async with AsyncSessionLocal() as session:
                await print_db_summary(session)

        print(f"\nСоздано новых: {stats['created']}, пропущено (уже есть): {stats['skipped']}")
        print_credentials_report()
        print("\nТестовые данные готовы.")

    except Exception as exc:
        print(f"\nОШИБКА: {exc}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
