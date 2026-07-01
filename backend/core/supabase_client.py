from functools import lru_cache

from supabase import Client, create_client

from core.config import settings


@lru_cache
def get_supabase_client() -> Client | None:
    """Инициализация клиента Supabase для Storage и других сервисов."""
    if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
        return None
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
