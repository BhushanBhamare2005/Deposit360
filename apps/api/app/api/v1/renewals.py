from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.permissions import can_review_finances, is_applicant
from app.db.session import get_db
from app.models.instrument import Instrument, InstrumentLifecycleState
from app.models.renewal_link import RenewalLink, RenewalRelationship
from app.models.user import User
from app.schemas.workflows import RenewalCreate, RenewalRead
from app.services.audit_service import record_event
from app.services.notification_service import notify_institution

router = APIRouter(prefix="/renewals", tags=["renewals"])


@router.post("", response_model=RenewalRead, status_code=status.HTTP_201_CREATED)
def link_renewal(
    payload: RenewalCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> RenewalLink:
    if not is_applicant(user.roles):
        raise HTTPException(
            status_code=403, detail="Only institution applicants can submit renewals"
        )
    previous = db.get(Instrument, payload.previous_instrument_id)
    replacement = db.get(Instrument, payload.replacement_instrument_id)
    if previous is None or replacement is None:
        raise HTTPException(status_code=404, detail="Deposit not found")
    if (
        previous.institution_id != user.institution_id
        or replacement.institution_id != user.institution_id
    ):
        raise HTTPException(status_code=404, detail="Deposit not found")
    if previous.id == replacement.id:
        raise HTTPException(status_code=409, detail="A deposit cannot renew itself")
    if previous.institution_id != replacement.institution_id:
        raise HTTPException(
            status_code=409,
            detail="Renewal deposits must belong to one institution",
        )
    if previous.maturity_date > replacement.maturity_date:
        raise HTTPException(
            status_code=422,
            detail="Replacement deposit must mature after the previous deposit",
        )
    if previous.lifecycle_state in {
        InstrumentLifecycleState.RELEASED,
        InstrumentLifecycleState.RENEWED,
    }:
        raise HTTPException(status_code=409, detail="Previous deposit is already closed")
    if replacement.lifecycle_state != InstrumentLifecycleState.ACTIVE:
        raise HTTPException(status_code=409, detail="Replacement deposit must be active")
    existing = db.scalar(
        select(RenewalLink).where(RenewalLink.previous_instrument_id == previous.id)
    )
    if existing:
        raise HTTPException(
            status_code=409,
            detail="Previous deposit already has a renewal link",
        )

    link = RenewalLink(
        previous_instrument_id=previous.id,
        replacement_instrument_id=replacement.id,
        status=RenewalRelationship.CONFIRMED,
    )
    previous.lifecycle_state = InstrumentLifecycleState.RENEWED
    db.add(link)
    db.flush()
    record_event(
        db,
        actor_id=user.id,
        action="renewal.linked",
        resource_type="renewal_link",
        resource_id=link.id,
        details={
            "previous_instrument_id": str(previous.id),
            "replacement_instrument_id": str(replacement.id),
        },
    )
    notify_institution(
        db,
        institution_id=previous.institution_id,
        instrument_id=previous.id,
        subject="Deposit renewal recorded",
        body=f"{previous.instrument_number} was renewed as {replacement.instrument_number}.",
    )
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409, detail="Deposit is already linked in a renewal"
        ) from exc
    db.refresh(link)
    return link


@router.get("", response_model=list[RenewalRead])
def list_renewals(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[RenewalLink]:
    if not (is_applicant(user.roles) or can_review_finances(user.roles)):
        raise HTTPException(
            status_code=403,
            detail="Renewal access is restricted to institution and finance roles",
        )
    statement = select(RenewalLink)
    if not can_review_finances(user.roles):
        if user.institution_id is None:
            return []
        statement = statement.join(
            Instrument,
            Instrument.id == RenewalLink.previous_instrument_id,
        ).where(Instrument.institution_id == user.institution_id)
    return list(db.scalars(statement.order_by(RenewalLink.created_at.desc())).unique().all())
