import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.notification import Notification, NotificationStatus
from app.models.user import User
from app.schemas.workflows import NotificationRead

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=list[NotificationRead])
def list_notifications(
    unread_only: bool = Query(default=False),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[Notification]:
    statement = select(Notification).where(Notification.recipient_user_id == user.id)
    if unread_only:
        statement = statement.where(Notification.status != NotificationStatus.ACKNOWLEDGED)
    return list(db.scalars(statement.order_by(Notification.created_at.desc()).limit(100)).all())


@router.patch("/{notification_id}/acknowledge", response_model=NotificationRead)
def acknowledge_notification(
    notification_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Notification:
    notification = db.scalar(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.recipient_user_id == user.id,
        )
    )
    if notification is None:
        raise HTTPException(status_code=404, detail="Notification not found")
    notification.status = NotificationStatus.ACKNOWLEDGED
    db.commit()
    db.refresh(notification)
    return notification
