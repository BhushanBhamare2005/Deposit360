import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.compliance_case import CaseStatus
from app.schemas.common import ReadModel


class CaseCreate(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=5, max_length=5000)


class CaseReview(BaseModel):
    status: CaseStatus
    resolution_note: str | None = Field(default=None, max_length=5000)


class CaseRead(ReadModel):
    id: uuid.UUID
    instrument_id: uuid.UUID
    title: str
    description: str
    status: CaseStatus
    resolution_note: str | None
    created_by: uuid.UUID
    reviewed_by: uuid.UUID | None
    created_at: datetime
