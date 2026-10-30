import uuid
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field, model_validator

from app.schemas.common import ReadModel


class PolicyRuleCreate(BaseModel):
    key: str = Field(min_length=2, max_length=100, pattern=r"^[a-z0-9][a-z0-9_.-]*$")
    description: str = Field(min_length=5, max_length=500)
    config: dict[str, Any] = Field(default_factory=dict)
    effective_from: date
    effective_to: date | None = None

    @model_validator(mode="after")
    def validate_effective_dates(self):
        if self.effective_to is not None and self.effective_to < self.effective_from:
            raise ValueError("effective_to cannot be before effective_from")
        return self


class PolicyRuleRead(ReadModel):
    id: uuid.UUID
    key: str
    version: int
    description: str
    config: dict[str, Any]
    effective_from: date
    effective_to: date | None
    created_at: datetime
