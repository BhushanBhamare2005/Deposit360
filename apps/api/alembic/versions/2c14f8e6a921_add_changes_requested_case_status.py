"""Add changes-requested case status.

Revision ID: 2c14f8e6a921
Revises: 1b29d7c6f4a1
"""

from collections.abc import Sequence

from alembic import op

revision: str = "2c14f8e6a921"
down_revision: str | None = "1b29d7c6f4a1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        op.execute("ALTER TYPE case_status ADD VALUE IF NOT EXISTS 'CHANGES_REQUESTED'")


def downgrade() -> None:
    pass
