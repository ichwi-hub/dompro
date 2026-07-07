import mimetypes
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile, status

from core.storage import get_storage_backend

ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png"}
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


async def validate_file(file: UploadFile) -> bytes:
    """Валидация загружаемого файла: тип и размер."""
    content = await file.read()
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Файл {file.filename} пустой",
        )
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Файл {file.filename} превышает 10 МБ",
        )

    ext = Path(file.filename or "").suffix.lower()
    mime = file.content_type or mimetypes.guess_type(file.filename or "")[0]

    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Недопустимый формат файла: {ext}. Разрешены: pdf, jpg, png",
        )
    if mime and mime not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Недопустимый MIME-тип: {mime}",
        )
    return content


async def upload_verification_file(
    file: UploadFile,
    expert_id: int,
    file_type: str,
) -> str:
    """Загрузка файла верификации через настроенный StorageBackend."""
    content = await validate_file(file)
    ext = Path(file.filename or "file").suffix.lower() or ".pdf"
    object_key = f"verifications/{expert_id}/{file_type}_{uuid.uuid4().hex}{ext}"

    mime = file.content_type or mimetypes.guess_type(file.filename or "")[0] or "application/octet-stream"
    backend = get_storage_backend()

    try:
        return await backend.save(object_key, content, mime)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка загрузки файла: {exc}",
        ) from exc
