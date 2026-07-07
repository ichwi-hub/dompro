"""Фабрика бэкенда хранилища."""

from __future__ import annotations

from functools import lru_cache

from core.config import settings
from core.storage.base import StorageBackend
from core.storage.local import LocalFilesystemStorage


@lru_cache
def get_storage_backend() -> StorageBackend:
    backend = settings.STORAGE_BACKEND.lower()
    if backend == "local":
        return LocalFilesystemStorage()
    if backend in {"s3", "object"}:
        raise NotImplementedError(
            "S3-совместимое хранилище будет добавлено при переезде на Yandex/VK Cloud"
        )
    raise ValueError(f"Неизвестный STORAGE_BACKEND: {settings.STORAGE_BACKEND}")
