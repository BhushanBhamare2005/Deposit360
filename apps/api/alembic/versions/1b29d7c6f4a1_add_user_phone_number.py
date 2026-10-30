"""Add user phone numbers for SMS notifications.

Revision ID: 1b29d7c6f4a1
Revises: e0da1ab6b2fa
Create Date: 2026-10-30
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "1b29d7c6f4a1"
down_revision: str | None = "e0da1ab6b2fa"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("phone_number", sa.String(length=32), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "phone_number")
