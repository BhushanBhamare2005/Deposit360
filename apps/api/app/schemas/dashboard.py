from decimal import Decimal

from pydantic import BaseModel


class DashboardSummary(BaseModel):
    total_instruments: int
    active_instruments: int
    approaching_maturity: int
    total_value: Decimal
    open_cases: int
