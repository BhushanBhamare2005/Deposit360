import uuid
from datetime import datetime
from typing import Any

from app.schemas.common import ReadModel


class AuditEventRead(ReadModel):
    id: uuid.UUID
    actor_id: uuid.UUID | None
    action: str
    resource_type: str
    resource_id: str
    details: dict[str, Any]
    created_at: datetime
