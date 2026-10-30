import uuid
from datetime import datetime

from app.models.document import DocumentStatus
from app.schemas.common import ReadModel


class DocumentRead(ReadModel):
    id: uuid.UUID
    instrument_id: uuid.UUID
    original_filename: str
    mime_type: str
    size_bytes: int
    sha256: str
    status: DocumentStatus
    uploaded_by: uuid.UUID | None
    created_at: datetime
