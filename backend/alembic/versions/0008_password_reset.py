"""Password reset tokens

Revision ID: 0008
Revises: 0007
Create Date: 2026-09-18
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("reset_token_hash", sa.String(length=64), nullable=True))
    op.add_column("users", sa.Column("reset_expires_at", sa.DateTime(timezone=True), nullable=True))
    op.create_unique_constraint("uq_users_reset_token_hash", "users", ["reset_token_hash"])


def downgrade() -> None:
    op.drop_constraint("uq_users_reset_token_hash", "users", type_="unique")
    op.drop_column("users", "reset_expires_at")
    op.drop_column("users", "reset_token_hash")
