from __future__ import annotations

import uuid
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.instrument import Instrument


class ReleaseStatus(StrEnum):
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"


class ReleaseRequest(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "release_requests"

    instrument_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("instruments.id", ondelete="CASCADE"), nullable=False, index=True
    )
    requested_by: Mapped[uuid.UUID] = mapped_column(nullable=False)
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    status: Mapped[ReleaseStatus] = mapped_column(
        Enum(ReleaseStatus, name="release_status"),
        nullable=False,
        default=ReleaseStatus.SUBMITTED,
    )
    justification: Mapped[str] = mapped_column(String(2000), nullable=False)
    review_note: Mapped[str | None] = mapped_column(String(2000), nullable=True)

    instrument: Mapped[Instrument] = relationship(back_populates="release_requests")
