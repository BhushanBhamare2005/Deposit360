import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.notification import NotificationChannel, NotificationStatus
from app.models.release_request import ReleaseStatus
from app.models.renewal_link import RenewalRelationship
from app.models.verification_check import VerificationStatus
from app.schemas.common import ReadModel


class RenewalCreate(BaseModel):
    previous_instrument_id: uuid.UUID
    replacement_instrument_id: uuid.UUID


class RenewalRead(ReadModel):
    id: uuid.UUID
    previous_instrument_id: uuid.UUID
    replacement_instrument_id: uuid.UUID
    status: RenewalRelationship
    created_at: datetime


class ReleaseCreate(BaseModel):
    justification: str = Field(min_length=10, max_length=2000)


class ReleaseReview(BaseModel):
    status: ReleaseStatus
    review_note: str | None = Field(default=None, max_length=2000)


class ReleaseRead(ReadModel):
    id: uuid.UUID
    instrument_id: uuid.UUID
    requested_by: uuid.UUID
    reviewed_by: uuid.UUID | None
    status: ReleaseStatus
    justification: str
    review_note: str | None
    created_at: datetime


class NotificationRead(ReadModel):
    id: uuid.UUID
    instrument_id: uuid.UUID | None
    recipient_user_id: uuid.UUID
    channel: NotificationChannel
    subject: str
    body: str
    status: NotificationStatus
    created_at: datetime


class VerificationCreate(BaseModel):
    instrument_id: uuid.UUID


class VerificationReview(BaseModel):
    status: VerificationStatus
    evidence_note: str = Field(min_length=5, max_length=1000)


class VerificationRead(ReadModel):
    id: uuid.UUID
    instrument_id: uuid.UUID
    check_type: str
    source: str
    status: VerificationStatus
    evidence_note: str | None
    requested_by: uuid.UUID | None
    reviewed_by: uuid.UUID | None
    created_at: datetime


class ExtractedFieldRead(ReadModel):
    id: uuid.UUID
    field_name: str
    extracted_value: str
    page_number: int | None
    confidence: float | None


class ExtractionRead(BaseModel):
    document_id: uuid.UUID
    text: str
    fields: list[ExtractedFieldRead]
    ocr_used: bool
