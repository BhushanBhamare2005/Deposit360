from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.permissions import can_manage_compliance
from app.db.session import get_db
from app.models.policy_rule import PolicyRule
from app.models.user import User
from app.schemas.policy_rule import PolicyRuleCreate, PolicyRuleRead
from app.services.audit_service import record_event

router = APIRouter(prefix="/policy-rules", tags=["compliance policy"])


def _require_compliance_admin(user: User) -> None:
    if not can_manage_compliance(user.roles):
        raise HTTPException(status_code=403, detail="Compliance administrator permission required")


@router.get("", response_model=list[PolicyRuleRead])
def list_policy_rules(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[PolicyRule]:
    _require_compliance_admin(user)
    return list(
        db.scalars(select(PolicyRule).order_by(PolicyRule.key, PolicyRule.version.desc())).all()
    )


@router.post("", response_model=PolicyRuleRead, status_code=status.HTTP_201_CREATED)
def create_policy_rule(
    payload: PolicyRuleCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> PolicyRule:
    _require_compliance_admin(user)
    latest = db.scalar(
        select(PolicyRule)
        .where(PolicyRule.key == payload.key)
        .order_by(PolicyRule.version.desc())
        .limit(1)
    )
    if latest and payload.effective_from <= latest.effective_from:
        raise HTTPException(
            status_code=409,
            detail="A new rule version must start after the current version",
        )
    if latest:
        latest.effective_to = payload.effective_from - timedelta(days=1)
    rule = PolicyRule(
        key=payload.key,
        version=(latest.version + 1) if latest else 1,
        description=payload.description.strip(),
        config=payload.config,
        effective_from=payload.effective_from,
        effective_to=payload.effective_to,
    )
    db.add(rule)
    db.flush()
    record_event(
        db,
        actor_id=user.id,
        action="policy_rule.created",
        resource_type="policy_rule",
        resource_id=rule.id,
        details={"key": rule.key, "version": rule.version},
    )
    db.commit()
    db.refresh(rule)
    return rule
