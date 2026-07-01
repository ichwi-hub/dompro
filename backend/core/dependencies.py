from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.database import get_db
from core.security import decode_access_token
from models.enums import UserRole, VerificationStatus
from models.expert import Expert
from models.user import User

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Загрузка текущего пользователя по JWT из заголовка Authorization."""
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Требуется авторизация",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_access_token(credentials.credentials)
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Невалидный токен",
            )
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Невалидный или просроченный токен",
        ) from exc

    result = await db.execute(
        select(User)
        .options(selectinload(User.expert))
        .where(User.id == int(user_id))
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Пользователь не найден",
        )
    return user


async def get_current_expert(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Expert:
    """Проверка, что текущий пользователь — эксперт с профилем."""
    if user.role != UserRole.EXPERT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ только для экспертов",
        )
    if user.expert is not None:
        user.expert.user = user
        return user.expert

    result = await db.execute(
        select(Expert)
        .options(selectinload(Expert.user))
        .where(Expert.user_id == user.id)
    )
    expert = result.scalar_one_or_none()
    if expert is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Профиль эксперта не найден",
        )
    return expert


async def get_verified_expert(
    user: User = Depends(get_current_user),
) -> Expert:
    """Проверка, что эксперт верифицирован (для откликов на заказы)."""
    expert = await get_current_expert(user)
    if user.verification_status != VerificationStatus.VERIFIED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Верификация не пройдена. Отклики на заказы недоступны.",
        )
    return expert


async def get_current_admin(
    user: User = Depends(get_current_user),
) -> User:
    """Проверка, что текущий пользователь — администратор."""
    if user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ только для администраторов",
        )
    return user
