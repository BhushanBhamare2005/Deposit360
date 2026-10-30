import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.permissions import can_view_audit
from app.db.session import get_db
from app.models.audit_event import AuditEvent
from app.models.user import User
from app.schemas.audit import AuditEventRead

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("", response_model=list[AuditEventRead])
def list_audit_events(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[AuditEvent]:
    if not can_view_audit(user.roles):
        raise HTTPException(status_code=403, detail="Audit permission required")
    statement = (
        select(AuditEvent).order_by(AuditEvent.created_at.desc()).offset(offset).limit(limit)
    )
    return list(db.scalars(statement).all())


@router.get("/{event_id}", response_model=AuditEventRead)
def get_audit_event(
    event_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AuditEvent:
    if not can_view_audit(user.roles):
        raise HTTPException(status_code=403, detail="Audit permission required")
    event = db.get(AuditEvent, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Audit event not found")
    return event
