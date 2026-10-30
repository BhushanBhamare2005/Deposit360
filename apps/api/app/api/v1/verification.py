import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.permissions import can_review_verifications, is_staff
from app.db.session import get_db
from app.models.instrument import Instrument
from app.models.user import User
from app.models.verification_check import VerificationCheck, VerificationStatus
from app.schemas.workflows import VerificationRead, VerificationReview
from app.services.audit_service import record_event
from app.services.bank_verification_service import request_verification
from app.services.notification_service import notify_roles

router = APIRouter(prefix="/verification", tags=["verification"])
logger = logging.getLogger(__name__)


def _can_access(instrument: Instrument, user: User) -> bool:
    return is_staff(user.roles) or instrument.institution_id == user.institution_id


@router.post(
    "/instruments/{instrument_id}",
    response_model=VerificationRead,
    status_code=status.HTTP_201_CREATED,
)
def verify_instrument(
    instrument_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> VerificationCheck:
    if not can_review_verifications(user.roles):
        raise HTTPException(
            status_code=403,
            detail="Compliance administrator permission required to request bank verification",
        )
    instrument = db.get(Instrument, instrument_id)
    if instrument is None or not _can_access(instrument, user):
        raise HTTPException(status_code=404, detail="Deposit not found")
    try:
        result = request_verification(instrument.instrument_number, instrument.bank_name)
    except RuntimeError as exc:
        logger.error("Bank verification provider failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Bank verification provider failed",
        ) from exc
    check = VerificationCheck(
        instrument_id=instrument.id,
        check_type="bank_confirmation",
        source=result.source,
        status=VerificationStatus(result.status),
        evidence_note=result.note,
        requested_by=user.id,
    )
    db.add(check)
    db.flush()
    record_event(
        db,
        actor_id=user.id,
        action="verification.requested",
        resource_type="verification_check",
        resource_id=check.id,
        details={"status": check.status.value, "source": check.source},
    )
    notify_roles(
        db,
        roles={"admin", "compliance_administrator", "scrutiny_officer"},
        instrument_id=instrument.id,
        subject="Manual bank verification requested",
        body=(
            f"Verification requested for {instrument.instrument_number}; no bank API was contacted."
        ),
    )
    db.commit()
    db.refresh(check)
    return check


@router.get("/instruments/{instrument_id}", response_model=list[VerificationRead])
def list_verifications(
    instrument_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[VerificationCheck]:
    instrument = db.get(Instrument, instrument_id)
    if instrument is None or not _can_access(instrument, user):
        raise HTTPException(status_code=404, detail="Deposit not found")
    return list(
        db.scalars(
            select(VerificationCheck)
            .where(VerificationCheck.instrument_id == instrument_id)
            .order_by(VerificationCheck.created_at.desc())
        ).all()
    )


@router.patch("/{check_id}", response_model=VerificationRead)
def review_verification(
    check_id: uuid.UUID,
    payload: VerificationReview,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> VerificationCheck:
    if not can_review_verifications(user.roles):
        raise HTTPException(status_code=403, detail="Compliance verification permission required")
    check = db.get(VerificationCheck, check_id)
    if check is None:
        raise HTTPException(status_code=404, detail="Verification check not found")
    if check.status != VerificationStatus.UNABLE_TO_VERIFY:
        raise HTTPException(status_code=409, detail="Only manually pending checks can be reviewed")
    if payload.status not in {VerificationStatus.CONFIRMED, VerificationStatus.FAILED}:
        raise HTTPException(status_code=422, detail="Choose a confirmed or failed result")
    check.status = payload.status
    check.evidence_note = payload.evidence_note.strip()
    check.reviewed_by = user.id
    record_event(
        db,
        actor_id=user.id,
        action="verification.reviewed",
        resource_type="verification_check",
        resource_id=check.id,
        details={"status": check.status.value},
    )
    db.commit()
    db.refresh(check)
    return check
