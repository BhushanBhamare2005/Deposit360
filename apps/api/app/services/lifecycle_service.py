import uuid
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.instrument import Instrument, InstrumentLifecycleState
from app.models.notification import Notification, NotificationChannel
from app.services.notification_service import notify_institution

MATURITY_REMINDER_SUBJECT = "Deposit maturity reminder"
_MATURITY_NOTIFICATION_SUBJECTS = (
    "Deposit approaching maturity",
    "Deposit maturity date passed",
    MATURITY_REMINDER_SUBJECT,
)


def refresh_states(
    db: Session,
    *,
    today: date | None = None,
    institution_id: uuid.UUID | None = None,
) -> int:
    today = today or date.today()
    states = (InstrumentLifecycleState.ACTIVE, InstrumentLifecycleState.APPROACHING_MATURITY)
    statement = select(Instrument).where(Instrument.lifecycle_state.in_(states))
    if institution_id is not None:
        statement = statement.where(Instrument.institution_id == institution_id)
    instruments = db.scalars(statement).all()
    changed = 0
    for instrument in instruments:
        days_remaining = (instrument.maturity_date - today).days
        if days_remaining < 0:
            next_state = InstrumentLifecycleState.MATURED
        elif days_remaining <= 30:
            next_state = InstrumentLifecycleState.APPROACHING_MATURITY
        else:
            next_state = InstrumentLifecycleState.ACTIVE
        if instrument.lifecycle_state != next_state:
            previous_state = instrument.lifecycle_state
            instrument.lifecycle_state = next_state
            changed += 1
            if next_state in {
                InstrumentLifecycleState.APPROACHING_MATURITY,
                InstrumentLifecycleState.MATURED,
            }:
                notify_institution(
                    db,
                    institution_id=instrument.institution_id,
                    instrument_id=instrument.id,
                    subject=(
                        "Deposit approaching maturity"
                        if next_state == InstrumentLifecycleState.APPROACHING_MATURITY
                        else "Deposit maturity date passed"
                    ),
                    body=(
                        f"{instrument.instrument_number} changed from "
                        f"{previous_state.value} to {next_state.value}; "
                        f"maturity date: {instrument.maturity_date.isoformat()}."
                    ),
                )
    if changed:
        db.commit()
    return changed


def send_periodic_maturity_reminders(
    db: Session,
    *,
    interval_days: int = 1,
) -> int:
    cutoff = datetime.now(UTC) - timedelta(days=interval_days)
    instruments = db.scalars(
        select(Instrument).where(
            Instrument.lifecycle_state.in_(
                (
                    InstrumentLifecycleState.APPROACHING_MATURITY,
                    InstrumentLifecycleState.MATURED,
                )
            )
        )
    ).all()
    created = 0
    for instrument in instruments:
        recent_reminder = db.scalar(
            select(Notification.id)
            .where(
                Notification.instrument_id == instrument.id,
                Notification.channel == NotificationChannel.IN_APP,
                Notification.subject.in_(_MATURITY_NOTIFICATION_SUBJECTS),
                Notification.created_at >= cutoff,
            )
            .limit(1)
        )
        if recent_reminder is not None:
            continue
        notify_institution(
            db,
            institution_id=instrument.institution_id,
            instrument_id=instrument.id,
            subject=MATURITY_REMINDER_SUBJECT,
            body=(
                f"{instrument.instrument_number} is {instrument.lifecycle_state.value}; "
                f"maturity date: {instrument.maturity_date.isoformat()}."
            ),
        )
        created += 1
    if created:
        db.commit()
    return created
