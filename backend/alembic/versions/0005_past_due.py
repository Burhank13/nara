"""Past due account state

Revision ID: 0005
Revises: 0004
Create Date: 2026-09-17
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TYPE business_status ADD VALUE IF NOT EXISTS 'past_due' AFTER 'active'")
    op.add_column("businesses", sa.Column("past_due_since", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("businesses", "past_due_since")
    # Postgres cannot drop a value from an enum, so the type is rebuilt without it.
    op.execute("UPDATE businesses SET status = 'active' WHERE status = 'past_due'")
    op.execute("ALTER TYPE business_status RENAME TO business_status_old")
    op.execute(
        "CREATE TYPE business_status AS ENUM ('trialing', 'active', 'read_only', 'suspended', 'cancelled')"
    )
    op.execute(
        "ALTER TABLE businesses ALTER COLUMN status TYPE business_status USING status::text::business_status"
    )
    op.execute("DROP TYPE business_status_old")
