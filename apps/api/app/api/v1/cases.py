import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.permissions import can_read_cases, can_review_cases, is_applicant
from app.db.session import get_db
from app.models.compliance_case import CaseStatus, ComplianceCase
from app.models.instrument import Instrument
from app.models.user import User
from app.schemas.case import CaseCreate, CaseRead, CaseReview
from app.services.audit_service import record_event
from app.services.notification_service import notify_institution, notify_roles

router = APIRouter(prefix="/cases", tags=["compliance cases"])


def _case_scope(user: User):
    statement = select(ComplianceCase).join(Instrument)
    if can_review_cases(user.roles):
        return statement
    if user.institution_id is None:
        return statement.where(False)
    return statement.where(Instrument.institution_id == user.institution_id)


@router.post(
    "/instruments/{instrument_id}",
    response_model=CaseRead,
    status_code=status.HTTP_201_CREATED,
)
def create_case(
    instrument_id: uuid.UUID,
    payload: CaseCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ComplianceCase:
    if not is_applicant(user.roles):
        raise HTTPException(status_code=403, detail="Only institution applicants can open cases")
    instrument = db.get(Instrument, instrument_id)
    if instrument is None or instrument.institution_id != user.institution_id:
        raise HTTPException(status_code=404, detail="Instrument not found")
    case = ComplianceCase(
        instrument_id=instrument_id,
        title=payload.title.strip(),
        description=payload.description.strip(),
        created_by=user.id,
    )
    db.add(case)
    db.flush()
    record_event(
        db,
        actor_id=user.id,
        action="case.created",
        resource_type="compliance_case",
        resource_id=case.id,
    )
    notify_institution(
        db,
        institution_id=instrument.institution_id,
        instrument_id=instrument.id,
        subject="Compliance case opened",
        body=f"A review case was opened for deposit {instrument.instrument_number}.",
    )
    db.commit()
    db.refresh(case)
    return case


@router.get("", response_model=list[CaseRead])
def list_cases(
    status_filter: CaseStatus | None = Query(default=None, alias="status"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[ComplianceCase]:
    if not can_read_cases(user.roles):
        raise HTTPException(
            status_code=403, detail="Case access is restricted to applicants and compliance roles"
        )
    statement = _case_scope(user)
    if status_filter is not None:
        statement = statement.where(ComplianceCase.status == status_filter)
    return list(db.scalars(statement.order_by(ComplianceCase.created_at.desc())).all())


@router.get("/{case_id}", response_model=CaseRead)
def get_case(
    case_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ComplianceCase:
    if not can_read_cases(user.roles):
        raise HTTPException(
            status_code=403, detail="Case access is restricted to applicants and compliance roles"
        )
    case = db.scalar(_case_scope(user).where(ComplianceCase.id == case_id))
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found")
    return case


@router.patch("/{case_id}", response_model=CaseRead)
def review_case(
    case_id: uuid.UUID,
    payload: CaseReview,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ComplianceCase:
    if not can_review_cases(user.roles):
        raise HTTPException(status_code=403, detail="Case review permission required")
    case = db.scalar(_case_scope(user).where(ComplianceCase.id == case_id))
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found")
    allowed_transitions = {
        CaseStatus.OPEN: {
            CaseStatus.IN_REVIEW,
            CaseStatus.CHANGES_REQUESTED,
            CaseStatus.APPROVED,
            CaseStatus.REJECTED,
        },
        CaseStatus.IN_REVIEW: {
            CaseStatus.CHANGES_REQUESTED,
            CaseStatus.APPROVED,
            CaseStatus.REJECTED,
        },
    }
    if payload.status not in allowed_transitions.get(case.status, set()):
        raise HTTPException(
            status_code=409,
            detail=f"Cannot change case from {case.status.value} to {payload.status.value}",
        )
    if payload.status == CaseStatus.CHANGES_REQUESTED and not payload.resolution_note:
        raise HTTPException(status_code=422, detail="A correction request must include a note")
    case.status = payload.status
    case.resolution_note = payload.resolution_note
    case.reviewed_by = user.id
    record_event(
        db,
        actor_id=user.id,
        action="case.reviewed",
        resource_type="compliance_case",
        resource_id=case.id,
        details={"status": payload.status.value},
    )
    notify_institution(
        db,
        institution_id=case.instrument.institution_id,
        instrument_id=case.instrument_id,
        subject="Compliance case updated",
        body=f"Case '{case.title}' was marked {case.status.value}.",
    )
    db.commit()
    db.refresh(case)
    return case


@router.post("/{case_id}/resubmit", response_model=CaseRead)
def resubmit_case(
    case_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ComplianceCase:
    if not is_applicant(user.roles):
        raise HTTPException(
            status_code=403, detail="Only institution applicants can resubmit cases"
        )
    case = db.scalar(_case_scope(user).where(ComplianceCase.id == case_id))
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found")
    if case.status != CaseStatus.CHANGES_REQUESTED:
        raise HTTPException(status_code=409, detail="This case is not awaiting corrections")
    case.status = CaseStatus.OPEN
    case.resolution_note = None
    case.reviewed_by = None
    record_event(
        db,
        actor_id=user.id,
        action="case.resubmitted",
        resource_type="compliance_case",
        resource_id=case.id,
    )
    notify_roles(
        db,
        roles={"scrutiny_officer", "compliance_administrator", "admin"},
        instrument_id=case.instrument_id,
        subject="Corrected deposit documents submitted",
        body=f"Updated evidence was submitted for case '{case.title}'.",
    )
    db.commit()
    db.refresh(case)
    return case
