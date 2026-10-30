from __future__ import annotations

import uuid
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.instrument import Instrument


class VerificationStatus(StrEnum):
    PENDING_EXTERNAL = "pending_external"
    CONFIRMED = "confirmed"
    FAILED = "failed"
    UNABLE_TO_VERIFY = "unable_to_verify"


class VerificationCheck(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "verification_checks"

    instrument_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("instruments.id", ondelete="CASCADE"), nullable=False, index=True
    )
    check_type: Mapped[str] = mapped_column(String(100), nullable=False)
    source: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[VerificationStatus] = mapped_column(
        Enum(VerificationStatus, name="verification_status"),
        nullable=False,
        default=VerificationStatus.PENDING_EXTERNAL,
    )
    evidence_note: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    requested_by: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(nullable=True)

    instrument: Mapped[Instrument] = relationship(back_populates="verification_checks")
