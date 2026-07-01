from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from models.enums import UserRole, VerificationStatus


class RegisterRequest(BaseModel):
    """Этап 1: регистрация аккаунта (30 секунд)."""

    phone: str = Field(min_length=10, max_length=32, examples=["+79001234567"])
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    """Вход по email или телефону."""

    login: str = Field(description="Email или номер телефона")
    password: str


class TokenResponse(BaseModel):
    """Ответ с JWT access-токеном."""

    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    """Публичные данные пользователя."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    phone: str
    role: UserRole
    full_name: str | None
    verification_status: VerificationStatus
    created_at: datetime
    updated_at: datetime


class LoginResponse(BaseModel):
    """Ответ при успешном входе."""

    access_token: str
    token_type: str = "bearer"
    user: UserResponse
