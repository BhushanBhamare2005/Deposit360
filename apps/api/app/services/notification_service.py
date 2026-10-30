import logging
import uuid

from sqlalchemy import event, select
from sqlalchemy.orm import Session

from app.adapters.email_sender import send_email
from app.adapters.sms_sender import send_sms
from app.models.notification import Notification, NotificationChannel, NotificationStatus
from app.models.user import User

logger = logging.getLogger(__name__)
_DELIVERY_QUEUE_KEY = "deposit360_notification_deliveries"


def _deliver(email: str, phone_number: str | None, subject: str, body: str) -> None:
    try:
        send_email(email, subject, body)
    except Exception:
        logger.exception("Email notification delivery failed")
    if phone_number:
        try:
            send_sms(phone_number, body)
        except Exception:
            logger.exception("SMS notification delivery failed")


@event.listens_for(Session, "after_commit")
def _deliver_after_commit(db: Session) -> None:
    deliveries = db.info.pop(_DELIVERY_QUEUE_KEY, ())
    for email, phone_number, subject, body in deliveries:
        _deliver(email, phone_number, subject, body)


@event.listens_for(Session, "after_rollback")
def _discard_rolled_back_deliveries(db: Session) -> None:
    db.info.pop(_DELIVERY_QUEUE_KEY, None)


def _queue_delivery(db: Session, user: User, subject: str, body: str) -> None:
    db.info.setdefault(_DELIVERY_QUEUE_KEY, []).append(
        (user.email, user.phone_number, subject, body)
    )


def notify_institution(
    db: Session,
    *,
    institution_id: uuid.UUID,
    instrument_id: uuid.UUID | None,
    subject: str,
    body: str,
    exclude_user_id: uuid.UUID | None = None,
) -> None:
    statement = select(User).where(User.institution_id == institution_id, User.is_active.is_(True))
    if exclude_user_id is not None:
        statement = statement.where(User.id != exclude_user_id)
    for user in db.scalars(statement):
        _queue_delivery(db, user, subject, body)
        db.add(
            Notification(
                recipient_user_id=user.id,
                instrument_id=instrument_id,
                channel=NotificationChannel.IN_APP,
                subject=subject,
                body=body,
                status=NotificationStatus.PENDING,
            )
        )


def notify_roles(
    db: Session,
    *,
    roles: set[str],
    instrument_id: uuid.UUID | None,
    subject: str,
    body: str,
) -> None:
    users = db.scalars(select(User).where(User.is_active.is_(True)))
    for user in users:
        if roles.intersection(user.roles):
            _queue_delivery(db, user, subject, body)
            db.add(
                Notification(
                    recipient_user_id=user.id,
                    instrument_id=instrument_id,
                    channel=NotificationChannel.IN_APP,
                    subject=subject,
                    body=body,
                    status=NotificationStatus.PENDING,
                )
            )
