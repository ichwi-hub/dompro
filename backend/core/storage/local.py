"""Локальное хранилище файлов на диске сервера."""

from __future__ import annotations

from pathlib import Path

from core.config import settings


class LocalFilesystemStorage:
    """Сохранение файлов в LOCAL_STORAGE_PATH."""

    def __init__(self, root: Path | None = None) -> None:
        self.root = (root or settings.local_storage_root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _full_path(self, key: str) -> Path:
        safe = key.replace("\\", "/").lstrip("/")
        target = (self.root / safe).resolve()
        if not str(target).startswith(str(self.root)):
            raise ValueError("Недопустимый путь к файлу")
        return target

    async def save(self, key: str, content: bytes, content_type: str) -> str:
        path = self._full_path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return settings.file_public_url(key)

    def resolve_path(self, key: str) -> str:
        return str(self._full_path(key))
