"""Абстракция файлового хранилища (локальная ФС сейчас, S3-совместимое — позже)."""

from __future__ import annotations

from typing import Protocol


class StorageBackend(Protocol):
    """Контракт бэкенда хранилища — provider-agnostic."""

    async def save(self, key: str, content: bytes, content_type: str) -> str:
        """Сохранить файл и вернуть публичный/доступный URL или ключ."""

    def resolve_path(self, key: str) -> str:
        """Локальный путь или URI для чтения (для отдачи через API)."""
