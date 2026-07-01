from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.dependencies import get_current_user
from core.security import create_access_token, hash_password, verify_password
from models.enums import UserRole, VerificationStatus
from models.expert import Expert
from models.user import User
from schemas.user import (
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)

router = APIRouter(prefix="/auth", tags=["Авторизация"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    payload: RegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Этап 1: регистрация эксперта (phone, email, password).

    Создаёт пользователя со статусом unverified.
    Без верификации отклики на заказы недоступны.
    """
    existing = await db.execute(
        select(User).where(
            or_(User.email == payload.email.lower(), User.phone == payload.phone)
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пользователь с таким email или телефоном уже существует",
        )

    user = User(
        email=payload.email.lower(),
        phone=payload.phone,
        password_hash=hash_password(payload.password),
        role=UserRole.EXPERT,
        verification_status=VerificationStatus.UNVERIFIED,
    )
    db.add(user)
    await db.flush()

    expert = Expert(user_id=user.id)
    db.add(expert)
    await db.commit()
    await db.refresh(user)

    token = create_access_token({"sub": str(user.id), "role": user.role.value})
    return TokenResponse(access_token=token)


@router.post("/login", response_model=LoginResponse)
async def login(
    payload: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> LoginResponse:
    """Вход по email или телефону + пароль."""
    login_value = payload.login.strip().lower()

    result = await db.execute(
        select(User).where(
            or_(User.email == login_value, User.phone == payload.login.strip())
        )
    )
    user = result.scalar_one_or_none()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный логин или пароль",
        )

    token = create_access_token({"sub": str(user.id), "role": user.role.value})
    return LoginResponse(
        access_token=token,
        user=UserResponse.model_validate(user),
    )


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    """Данные текущего авторизованного пользователя."""
    return UserResponse.model_validate(current_user)
