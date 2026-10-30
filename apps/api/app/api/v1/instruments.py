import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.permissions import is_applicant, is_staff
from app.db.session import get_db
from app.models.instrument import Instrument
from app.models.user import User
from app.schemas.instrument import InstrumentCreate, InstrumentList, InstrumentRead
from app.services.audit_service import record_event
from app.services.lifecycle_service import refresh_states

router = APIRouter(prefix="/instruments", tags=["instruments"])


def _apply_institution_scope(statement, user: User):
    if is_staff(user.roles):
        return statement
    if user.institution_id is None:
        return statement.where(False)
    return statement.where(Instrument.institution_id == user.institution_id)


@router.post("", response_model=InstrumentRead, status_code=status.HTTP_201_CREATED)
def create_instrument(
    payload: InstrumentCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Instrument:
    if not is_applicant(user.roles):
        raise HTTPException(
            status_code=403, detail="Only institution applicants can register deposits"
        )
    if user.institution_id is None:
        raise HTTPException(status_code=409, detail="Create or join an institution first")
    instrument = Instrument(
        institution_id=user.institution_id,
        instrument_number=payload.instrument_number.strip(),
        bank_name=payload.bank_name.strip(),
        branch_name=payload.branch_name.strip() if payload.branch_name else None,
        holder_name=payload.holder_name.strip(),
        amount=payload.amount,
        issue_date=payload.issue_date,
        maturity_date=payload.maturity_date,
    )
    db.add(instrument)
    db.flush()
    record_event(
        db,
        actor_id=user.id,
        action="instrument.created",
        resource_type="instrument",
        resource_id=instrument.id,
    )
    db.commit()
    db.refresh(instrument)
    return instrument


@router.get("", response_model=InstrumentList)
def list_instruments(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> InstrumentList:
    if is_staff(user.roles):
        refresh_states(db)
    elif user.institution_id is not None:
        refresh_states(db, institution_id=user.institution_id)
    statement = _apply_institution_scope(select(Instrument), user)
    count_statement = _apply_institution_scope(select(func.count()).select_from(Instrument), user)
    total = db.scalar(count_statement) or 0
    records = db.scalars(
        statement.order_by(Instrument.maturity_date).offset(offset).limit(limit)
    ).all()
    return InstrumentList(items=list(records), total=total)


@router.get("/{instrument_id}", response_model=InstrumentRead)
def get_instrument(
    instrument_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Instrument:
    statement = _apply_institution_scope(select(Instrument), user).where(
        Instrument.id == instrument_id
    )
    instrument = db.scalar(statement)
    if instrument is None:
        raise HTTPException(status_code=404, detail="Instrument not found")
    return instrument
