"""Shift edit audit log

Revision ID: 0004
Revises: 0003
Create Date: 2026-09-17
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "shift_edits",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("shift_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("edited_by_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("previous_started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("previous_ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("new_started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("new_ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["shift_id"], ["shifts.id"], name="fk_shift_edits_shift_id_shifts", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["edited_by_id"], ["users.id"], name="fk_shift_edits_edited_by_id_users", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_shift_edits"),
    )
    op.create_index("ix_shift_edits_shift_id", "shift_edits", ["shift_id"])


def downgrade() -> None:
    op.drop_index("ix_shift_edits_shift_id", table_name="shift_edits")
    op.drop_table("shift_edits")
