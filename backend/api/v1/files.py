from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse

from core.config import settings
from core.dependencies import get_current_admin
from core.storage import get_storage_backend
from models.user import User

router = APIRouter(tags=["Файлы"])


@router.get("/files/{file_path:path}")
async def get_stored_file(
    file_path: str,
    _: User = Depends(get_current_admin),
) -> FileResponse:
    """Отдача файлов верификации (только администратор)."""
    key = file_path.replace("\\", "/").lstrip("/")
    if not key.startswith("verifications/"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Доступ запрещён")

    backend = get_storage_backend()
    full_path = Path(backend.resolve_path(key))
    if not full_path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Файл не найден")

    return FileResponse(full_path)
