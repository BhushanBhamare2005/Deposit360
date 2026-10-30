from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.permissions import is_applicant
from app.db.session import get_db
from app.models.institution import Institution
from app.models.user import User
from app.schemas.institution import InstitutionCreate, InstitutionRead
from app.services.audit_service import record_event

router = APIRouter(prefix="/institutions", tags=["institutions"])


@router.post("", response_model=InstitutionRead, status_code=status.HTTP_201_CREATED)
def create_institution(
    payload: InstitutionCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Institution:
    if not is_applicant(user.roles):
        raise HTTPException(
            status_code=403, detail="Only institution applicants can create an institution"
        )
    if user.institution_id is not None:
        raise HTTPException(
            status_code=409,
            detail="Your account already belongs to an institution",
        )
    institution = Institution(
        code=payload.code.strip().upper(),
        name=payload.name.strip(),
        approval_reference=payload.approval_reference,
        contact_email=str(payload.contact_email).lower(),
    )
    db.add(institution)
    try:
        db.flush()
        user.institution_id = institution.id
        record_event(
            db,
            actor_id=user.id,
            action="institution.created",
            resource_type="institution",
            resource_id=institution.id,
        )
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Institution code is already in use") from exc
    db.refresh(institution)
    return institution


@router.get("/me", response_model=InstitutionRead)
def get_my_institution(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Institution:
    if user.institution_id is None:
        raise HTTPException(status_code=404, detail="No institution is linked to this account")
    institution = db.scalar(select(Institution).where(Institution.id == user.institution_id))
    if institution is None:
        raise HTTPException(status_code=404, detail="Institution not found")
    return institution
