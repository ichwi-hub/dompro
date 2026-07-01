from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.database import get_db
from core.dependencies import get_current_expert
from models.enums import ExpertVerificationStatus, VerificationStatus
from models.expert import Expert
from models.verification import ExpertVerification
from schemas.verification import VerificationStatusResponse
from services.fns_api import check_inn, notify_admin_new_verification
from services.storage import upload_verification_file

router = APIRouter(prefix="/expert/verification", tags=["Верификация эксперта"])


@router.post("/submit", response_model=VerificationStatusResponse)
async def submit_verification(
    inn: str = Form(..., description="ИНН (10 или 12 цифр)"),
    diploma_file: UploadFile = File(..., description="Скан диплома"),
    self_employment_file: UploadFile = File(..., description="Статус самозанятого/ИП"),
    bar_association_file: UploadFile | None = File(
        None,
        description="Адвокатское удостоверение (опционально)",
    ),
    expert: Expert = Depends(get_current_expert),
    db: AsyncSession = Depends(get_db),
) -> VerificationStatusResponse:
    """Этап 3: подача документов на верификацию.

    Требует заполненного профиля. ИНН проверяется автоматически (заглушка ФНС).
    Документы загружаются в Supabase Storage.
    """
    if not expert.is_profile_complete:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Сначала заполните профиль эксперта",
        )

    if expert.user.verification_status == VerificationStatus.VERIFIED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Вы уже верифицированы",
        )

    if expert.user.verification_status == VerificationStatus.VERIFICATION_PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Заявка на верификацию уже на рассмотрении",
        )

    inn_result = check_inn(inn)
    if not inn_result.valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=inn_result.message,
        )

    cleaned_inn = "".join(c for c in inn if c.isdigit())

    diploma_url = await upload_verification_file(diploma_file, expert.id, "diploma")
    self_employment_url = await upload_verification_file(
        self_employment_file, expert.id, "self_employment"
    )
    bar_association_url = None
    if bar_association_file and bar_association_file.filename:
        bar_association_url = await upload_verification_file(
            bar_association_file, expert.id, "bar_association"
        )

    verification = ExpertVerification(
        expert_id=expert.id,
        inn=cleaned_inn,
        diploma_url=diploma_url,
        self_employment_url=self_employment_url,
        bar_association_url=bar_association_url,
        status=ExpertVerificationStatus.PENDING,
    )
    db.add(verification)

    expert.inn = cleaned_inn
    expert.diploma_url = diploma_url
    expert.self_employment_url = self_employment_url
    expert.bar_association_url = bar_association_url
    expert.updated_at = datetime.now(timezone.utc)

    expert.user.verification_status = VerificationStatus.VERIFICATION_PENDING
    expert.user.updated_at = datetime.now(timezone.utc)

    await db.flush()
    notify_admin_new_verification(expert.id, verification.id)
    await db.commit()

    return VerificationStatusResponse(
        verification_status=expert.user.verification_status,
        latest_request_status=verification.status,
        rejection_reason=None,
        is_profile_complete=True,
        can_submit=False,
    )


@router.get("/status", response_model=VerificationStatusResponse)
async def get_verification_status(
    expert: Expert = Depends(get_current_expert),
    db: AsyncSession = Depends(get_db),
) -> VerificationStatusResponse:
    """Статус верификации текущего эксперта."""
    result = await db.execute(
        select(ExpertVerification)
        .where(ExpertVerification.expert_id == expert.id)
        .order_by(ExpertVerification.created_at.desc())
        .limit(1)
    )
    latest = result.scalar_one_or_none()

    can_submit = (
        expert.is_profile_complete
        and expert.user.verification_status
        in (VerificationStatus.UNVERIFIED, VerificationStatus.REJECTED)
    )

    return VerificationStatusResponse(
        verification_status=expert.user.verification_status,
        latest_request_status=latest.status if latest else None,
        rejection_reason=expert.rejection_reason,
        is_profile_complete=expert.is_profile_complete,
        can_submit=can_submit,
    )
