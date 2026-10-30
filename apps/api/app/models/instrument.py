from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import Date, Enum, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.compliance_case import ComplianceCase
    from app.models.document import Document
    from app.models.institution import Institution
    from app.models.notification import Notification
    from app.models.release_request import ReleaseRequest
    from app.models.verification_check import VerificationCheck


class InstrumentLifecycleState(StrEnum):
    ACTIVE = "active"
    APPROACHING_MATURITY = "approaching_maturity"
    MATURED = "matured"
    RENEWED = "renewed"
    RELEASED = "released"


class Instrument(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "instruments"

    institution_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("institutions.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    instrument_number: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    bank_name: Mapped[str] = mapped_column(String(200), nullable=False)
    branch_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    holder_name: Mapped[str] = mapped_column(String(200), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(16, 2), nullable=False)
    issue_date: Mapped[date] = mapped_column(Date, nullable=False)
    maturity_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    lifecycle_state: Mapped[InstrumentLifecycleState] = mapped_column(
        Enum(InstrumentLifecycleState, name="instrument_lifecycle_state"),
        nullable=False,
        default=InstrumentLifecycleState.ACTIVE,
    )

    institution: Mapped[Institution] = relationship(back_populates="instruments")
    documents: Mapped[list[Document]] = relationship(
        back_populates="instrument", cascade="all, delete-orphan"
    )
    cases: Mapped[list[ComplianceCase]] = relationship(
        back_populates="instrument", cascade="all, delete-orphan"
    )
    verification_checks: Mapped[list[VerificationCheck]] = relationship(
        back_populates="instrument", cascade="all, delete-orphan"
    )
    release_requests: Mapped[list[ReleaseRequest]] = relationship(
        back_populates="instrument", cascade="all, delete-orphan"
    )
    notifications: Mapped[list[Notification]] = relationship(back_populates="instrument")
