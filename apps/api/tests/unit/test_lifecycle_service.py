from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app import models  # noqa: F401
from app.db.base import Base
from app.models.institution import Institution
from app.models.instrument import Instrument, InstrumentLifecycleState
from app.models.notification import Notification
from app.models.user import User
from app.services.lifecycle_service import refresh_states


def test_refresh_states_updates_maturity_and_preserves_closed_instruments():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    today = date(2030, 1, 1)
    with Session(engine) as db:
        institution = Institution(
            code="LIFECYCLE",
            name="Lifecycle Test",
            contact_email="lifecycle@example.com",
        )
        db.add(institution)
        db.flush()
        db.add(
            User(
                email="lifecycle@example.com",
                full_name="Lifecycle User",
                hashed_password="not-used",
                roles=["institution_user"],
                institution_id=institution.id,
            )
        )
        db.add_all(
            [
                Instrument(
                    institution_id=institution.id,
                    instrument_number="MATURING",
                    bank_name="Test Bank",
                    holder_name="Lifecycle Test",
                    amount=Decimal("1000.00"),
                    issue_date=today - timedelta(days=30),
                    maturity_date=today + timedelta(days=30),
                ),
                Instrument(
                    institution_id=institution.id,
                    instrument_number="MATURED",
                    bank_name="Test Bank",
                    holder_name="Lifecycle Test",
                    amount=Decimal("1000.00"),
                    issue_date=today - timedelta(days=60),
                    maturity_date=today - timedelta(days=1),
                ),
                Instrument(
                    institution_id=institution.id,
                    instrument_number="RELEASED",
                    bank_name="Test Bank",
                    holder_name="Lifecycle Test",
                    amount=Decimal("1000.00"),
                    issue_date=today - timedelta(days=60),
                    maturity_date=today - timedelta(days=1),
                    lifecycle_state=InstrumentLifecycleState.RELEASED,
                ),
            ]
        )
        db.commit()

        assert refresh_states(db, today=today) == 2
        states = {
            instrument.instrument_number: instrument.lifecycle_state
            for instrument in db.query(Instrument).all()
        }
        assert states == {
            "MATURING": InstrumentLifecycleState.APPROACHING_MATURITY,
            "MATURED": InstrumentLifecycleState.MATURED,
            "RELEASED": InstrumentLifecycleState.RELEASED,
        }
        assert db.query(Notification).count() == 2
        assert refresh_states(db, today=today) == 0
        assert db.query(Notification).count() == 2
