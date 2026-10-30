from datetime import date, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.permissions import can_read_cases, can_view_all_institutions
from app.db.session import get_db
from app.models.compliance_case import CaseStatus, ComplianceCase
from app.models.instrument import Instrument, InstrumentLifecycleState
from app.models.user import User
from app.schemas.dashboard import DashboardSummary

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummary)
def get_summary(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> DashboardSummary:
    instrument_statement = select(Instrument)
    case_statement = select(func.count(ComplianceCase.id)).join(Instrument)
    if not can_view_all_institutions(user.roles):
        instrument_statement = instrument_statement.where(
            Instrument.institution_id == user.institution_id
        )
        case_statement = case_statement.where(Instrument.institution_id == user.institution_id)
    case_count_statement = case_statement.where(ComplianceCase.status == CaseStatus.OPEN)

    instruments = db.scalars(instrument_statement).all()
    today = date.today()
    maturity_cutoff = today + timedelta(days=30)
    total_value = sum((row.amount for row in instruments), Decimal("0"))
    active_count = sum(
        row.lifecycle_state == InstrumentLifecycleState.ACTIVE for row in instruments
    )
    approaching_count = sum(
        today <= row.maturity_date <= maturity_cutoff
        and row.lifecycle_state
        not in {
            InstrumentLifecycleState.MATURED,
            InstrumentLifecycleState.RELEASED,
        }
        for row in instruments
    )
    return DashboardSummary(
        total_instruments=len(instruments),
        active_instruments=active_count,
        approaching_maturity=approaching_count,
        total_value=total_value,
        open_cases=(db.scalar(case_count_statement) or 0) if can_read_cases(user.roles) else 0,
    )
