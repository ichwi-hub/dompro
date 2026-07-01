from pydantic import BaseModel, ConfigDict, Field


class ClientCreate(BaseModel):
    """Создание профиля заказчика."""

    company_name: str | None = Field(default=None, max_length=255)


class ClientResponse(BaseModel):
    """Публичное представление заказчика."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    company_name: str | None
