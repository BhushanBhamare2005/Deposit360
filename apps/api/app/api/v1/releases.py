import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.permissions import (
    can_approve_releases,
    can_read_releases,
    can_review_finances,
    is_applicant,
)
from app.db.session import get_db
from app.models.instrument import Instrument, InstrumentLifecycleState
from app.models.release_request import ReleaseRequest, ReleaseStatus
from app.models.user import User
from app.schemas.workflows import ReleaseCreate, ReleaseRead, ReleaseReview
from app.services.audit_service import record_event
from app.services.notification_service import notify_institution, notify_roles

router = APIRouter(prefix="/releases", tags=["releases"])


def _scope(statement, user: User):
    if can_review_finances(user.roles) or can_approve_releases(user.roles):
        return statement
    if user.institution_id is None:
        return statement.where(False)
    return statement.join(Instrument).where(Instrument.institution_id == user.institution_id)


@router.post(
    "/instruments/{instrument_id}",
    response_model=ReleaseRead,
    status_code=status.HTTP_201_CREATED,
)
def request_release(
    instrument_id: uuid.UUID,
    payload: ReleaseCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ReleaseRequest:
    if not is_applicant(user.roles):
        raise HTTPException(
            status_code=403, detail="Only institution applicants can request a release"
        )
    instrument = db.get(Instrument, instrument_id)
    if instrument is None or instrument.institution_id != user.institution_id:
        raise HTTPException(status_code=404, detail="Deposit not found")
    if instrument.lifecycle_state in {
        InstrumentLifecycleState.RELEASED,
        InstrumentLifecycleState.RENEWED,
    }:
        raise HTTPException(status_code=409, detail="Closed deposits cannot be released")
    pending = db.scalar(
        select(ReleaseRequest).where(
            ReleaseRequest.instrument_id == instrument.id,
            ReleaseRequest.status.in_([ReleaseStatus.SUBMITTED, ReleaseStatus.UNDER_REVIEW]),
        )
    )
    if pending:
        raise HTTPException(status_code=409, detail="A release request is already open")

    request = ReleaseRequest(
        instrument_id=instrument.id,
        requested_by=user.id,
        justification=payload.justification.strip(),
    )
    db.add(request)
    db.flush()
    record_event(
        db,
        actor_id=user.id,
        action="release.requested",
        resource_type="release_request",
        resource_id=request.id,
    )
    notify_roles(
        db,
        roles={"finance_officer", "approving_authority", "admin"},
        instrument_id=instrument.id,
        subject="Release request submitted",
        body=f"A release request was submitted for {instrument.instrument_number}.",
    )
    db.commit()
    db.refresh(request)
    return request


@router.get("", response_model=list[ReleaseRead])
def list_releases(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[ReleaseRequest]:
    if not can_read_releases(user.roles):
        raise HTTPException(
            status_code=403, detail="Release access is restricted to applicants and finance roles"
        )
    statement = _scope(select(ReleaseRequest), user)
    return list(db.scalars(statement.order_by(ReleaseRequest.created_at.desc())).unique().all())


@router.get("/{request_id}", response_model=ReleaseRead)
def get_release(
    request_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ReleaseRequest:
    if not can_read_releases(user.roles):
        raise HTTPException(
            status_code=403, detail="Release access is restricted to applicants and finance roles"
        )
    request = db.scalar(_scope(select(ReleaseRequest), user).where(ReleaseRequest.id == request_id))
    if request is None:
        raise HTTPException(status_code=404, detail="Release request not found")
    return request


@router.patch("/{request_id}", response_model=ReleaseRead)
def review_release(
    request_id: uuid.UUID,
    payload: ReleaseReview,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ReleaseRequest:
    finance_reviewer = can_review_finances(user.roles)
    approving_authority = can_approve_releases(user.roles)
    legacy_admin = "admin" in user.roles
    if not (finance_reviewer or approving_authority):
        raise HTTPException(status_code=403, detail="Release review permission required")
    request = db.scalar(_scope(select(ReleaseRequest), user).where(ReleaseRequest.id == request_id))
    if request is None:
        raise HTTPException(status_code=404, detail="Release request not found")
    if legacy_admin:
        allowed_statuses = {
            ReleaseStatus.UNDER_REVIEW,
            ReleaseStatus.APPROVED,
            ReleaseStatus.REJECTED,
        }
    elif finance_reviewer:
        allowed_statuses = (
            {ReleaseStatus.UNDER_REVIEW} if request.status == ReleaseStatus.SUBMITTED else set()
        )
    else:
        allowed_statuses = (
            {ReleaseStatus.APPROVED, ReleaseStatus.REJECTED}
            if request.status == ReleaseStatus.UNDER_REVIEW
            else set()
        )
    if payload.status not in allowed_statuses:
        raise HTTPException(
            status_code=409,
            detail="This role cannot make that decision at the current release stage",
        )
    request.status = payload.status
    request.review_note = payload.review_note
    request.reviewed_by = user.id
    if payload.status == ReleaseStatus.APPROVED:
        instrument = db.get(Instrument, request.instrument_id)
        if instrument is None:
            raise HTTPException(status_code=404, detail="Deposit not found")
        instrument.lifecycle_state = InstrumentLifecycleState.RELEASED
    record_event(
        db,
        actor_id=user.id,
        action="release.reviewed",
        resource_type="release_request",
        resource_id=request.id,
        details={"status": payload.status.value},
    )
    instrument = db.get(Instrument, request.instrument_id)
    if instrument is not None:
        notify_institution(
            db,
            institution_id=instrument.institution_id,
            instrument_id=instrument.id,
            subject="Release request updated",
            body=(
                f"Your release request for {instrument.instrument_number} "
                f"is {payload.status.value}."
            ),
        )
        if payload.status == ReleaseStatus.UNDER_REVIEW:
            notify_roles(
                db,
                roles={"approving_authority", "admin"},
                instrument_id=instrument.id,
                subject="Finance review completed",
                body=(
                    f"Release request for {instrument.instrument_number} is ready "
                    "for final approval."
                ),
            )
    db.commit()
    db.refresh(request)
    return request
