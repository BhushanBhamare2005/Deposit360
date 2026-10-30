import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.schemas.common import ReadModel


class InstitutionCreate(BaseModel):
    code: str = Field(min_length=2, max_length=50, pattern=r"^[A-Za-z0-9_-]+$")
    name: str = Field(min_length=2, max_length=300)
    approval_reference: str | None = Field(default=None, max_length=100)
    contact_email: EmailStr


class InstitutionRead(ReadModel):
    id: uuid.UUID
    code: str
    name: str
    approval_reference: str | None
    contact_email: EmailStr
    created_at: datetime
