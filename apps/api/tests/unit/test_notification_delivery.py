from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app import models  # noqa: F401
from app.db.base import Base
from app.models.institution import Institution
from app.models.instrument import Instrument, InstrumentLifecycleState
from app.models.notification import Notification, NotificationStatus
from app.models.user import User
from app.services import notification_service
from app.services.lifecycle_service import send_periodic_maturity_reminders


def _session():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    return engine, Session(engine)


def test_email_failure_is_logged_without_losing_in_app_notification(monkeypatch):
    engine, db = _session()
    institution = Institution(
        code="DELIVERY",
        name="Delivery Test",
        contact_email="delivery@example.com",
    )
    db.add(institution)
    db.flush()
    db.add(
        User(
            email="user@example.com",
            full_name="Test User",
            hashed_password="not-used",
            roles=["institution_user"],
            institution_id=institution.id,
        )
    )
    db.commit()
    attempts = []
    reported_failures = []

    def fail_email(*_args):
        attempts.append(True)
        raise RuntimeError("provider unavailable")

    monkeypatch.setattr(notification_service, "send_email", fail_email)
    monkeypatch.setattr(
        notification_service.logger,
        "exception",
        lambda *_args: reported_failures.append(True),
    )

    notification_service.notify_institution(
        db,
        institution_id=institution.id,
        instrument_id=None,
        subject="Test",
        body="Notification body",
    )
    db.commit()

    notification = db.scalar(select(Notification))
    assert notification is not None
    assert notification.status == NotificationStatus.PENDING
    assert attempts == [True]
    assert reported_failures == [True]
    db.close()
    engine.dispose()


def test_periodic_maturity_notifications_are_deduplicated_until_interval_expires():
    engine, db = _session()
    institution = Institution(
        code="REMINDER",
        name="Reminder Test",
        contact_email="reminder@example.com",
    )
    db.add(institution)
    db.flush()
    db.add(
        User(
            email="reminder-user@example.com",
            full_name="Reminder User",
            hashed_password="not-used",
            roles=["institution_user"],
            institution_id=institution.id,
        )
    )
    db.add(
        Instrument(
            institution_id=institution.id,
            instrument_number="MATURITY-REMINDER",
            bank_name="Example Bank",
            holder_name="Reminder Test",
            amount=Decimal("1000.00"),
            issue_date=date.today() - timedelta(days=60),
            maturity_date=date.today() - timedelta(days=1),
            lifecycle_state=InstrumentLifecycleState.MATURED,
        )
    )
    db.commit()

    assert send_periodic_maturity_reminders(db, interval_days=1) == 1
    assert send_periodic_maturity_reminders(db, interval_days=1) == 0
    assert db.query(Notification).count() == 1

    db.close()
    engine.dispose()
