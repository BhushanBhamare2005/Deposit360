import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import Field, model_validator

from app.models.instrument import InstrumentLifecycleState
from app.schemas.common import ReadModel


class InstrumentCreate(ReadModel):
    instrument_number: str = Field(min_length=1, max_length=100)
    bank_name: str = Field(min_length=2, max_length=200)
    branch_name: str | None = Field(default=None, max_length=200)
    holder_name: str = Field(min_length=2, max_length=200)
    amount: Decimal = Field(gt=0, max_digits=16, decimal_places=2)
    issue_date: date
    maturity_date: date

    @model_validator(mode="after")
    def validate_dates(self) -> "InstrumentCreate":
        if self.maturity_date <= self.issue_date:
            raise ValueError("maturity_date must be after issue_date")
        return self


class InstrumentRead(ReadModel):
    id: uuid.UUID
    institution_id: uuid.UUID
    instrument_number: str
    bank_name: str
    branch_name: str | None
    holder_name: str
    amount: Decimal
    issue_date: date
    maturity_date: date
    lifecycle_state: InstrumentLifecycleState
    created_at: datetime


class InstrumentList(ReadModel):
    items: list[InstrumentRead]
    total: int
