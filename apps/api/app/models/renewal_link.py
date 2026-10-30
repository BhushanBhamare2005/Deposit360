import uuid
from enum import StrEnum

from sqlalchemy import Enum, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class RenewalRelationship(StrEnum):
    CONFIRMED = "confirmed"
    BROKEN = "broken"


class RenewalLink(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "renewal_links"
    __table_args__ = (
        UniqueConstraint("previous_instrument_id", name="uq_renewal_previous"),
        UniqueConstraint("replacement_instrument_id", name="uq_renewal_replacement"),
    )

    previous_instrument_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("instruments.id", ondelete="CASCADE"), nullable=False, index=True
    )
    replacement_instrument_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("instruments.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[RenewalRelationship] = mapped_column(
        Enum(RenewalRelationship, name="renewal_relationship"),
        nullable=False,
        default=RenewalRelationship.CONFIRMED,
    )
