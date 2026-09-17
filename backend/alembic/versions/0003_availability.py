"""Weekly availability

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-17
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "availability",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("weekday", sa.SmallInteger(), nullable=False),
        sa.Column("start_time", sa.Time(), nullable=False),
        sa.Column("end_time", sa.Time(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("weekday BETWEEN 0 AND 6", name="ck_availability_weekday_within_week"),
        sa.CheckConstraint("end_time > start_time", name="ck_availability_end_after_start"),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_availability_user_id_users", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_availability"),
        sa.UniqueConstraint("user_id", "weekday", name="uq_availability_user_id_weekday"),
    )
    op.create_index("ix_availability_user_id", "availability", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_availability_user_id", table_name="availability")
    op.drop_table("availability")
