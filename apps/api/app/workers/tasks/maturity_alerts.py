from app.core.config import get_settings
from app.db.session import SessionLocal
from app.services.lifecycle_service import (
    refresh_states,
    send_periodic_maturity_reminders,
)


def run_maturity_alerts() -> tuple[int, int]:
    settings = get_settings()
    with SessionLocal() as db:
        changed = refresh_states(db)
        reminders = send_periodic_maturity_reminders(
            db,
            interval_days=settings.maturity_reminder_interval_days,
        )
    return changed, reminders
