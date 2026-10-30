import uuid
from datetime import datetime

from pydantic import EmailStr

from app.schemas.common import ReadModel


class UserRead(ReadModel):
    id: uuid.UUID
    email: EmailStr
    full_name: str
    phone_number: str | None = None
    roles: list[str]
    is_active: bool
    institution_id: uuid.UUID | None
    created_at: datetime
