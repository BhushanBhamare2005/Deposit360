import pytest
from pydantic import ValidationError

from app.schemas.instrument import InstrumentCreate


def test_instrument_rejects_maturity_before_issue_date():
    with pytest.raises(ValidationError, match="maturity_date must be after issue_date"):
        InstrumentCreate(
            instrument_number="FDR-1",
            bank_name="Example Bank",
            holder_name="Example Institution",
            amount="100.00",
            issue_date="2030-01-02",
            maturity_date="2030-01-01",
        )
