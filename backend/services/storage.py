import mimetypes
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile, status

from core.config import settings
from core.supabase_client import get_supabase_client

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
    """Загрузка файла верификации в Supabase Storage."""
    content = await validate_file(file)
    ext = Path(file.filename or "file").suffix.lower() or ".pdf"
    object_path = f"{expert_id}/{file_type}_{uuid.uuid4().hex}{ext}"

    client = get_supabase_client()
    if client is None:
        # Локальная заглушка без Supabase — для разработки
        return f"local://verifications/{object_path}"

    bucket = settings.SUPABASE_STORAGE_BUCKET
    mime = file.content_type or mimetypes.guess_type(file.filename or "")[0] or "application/octet-stream"

    try:
        client.storage.from_(bucket).upload(
            path=object_path,
            file=content,
            file_options={"content-type": mime, "upsert": "true"},
        )
        public = client.storage.from_(bucket).get_public_url(object_path)
        return public
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка загрузки файла в Storage: {exc}",
        ) from exc
