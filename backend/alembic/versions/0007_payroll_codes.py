"""Payroll codes for export

Revision ID: 0007
Revises: 0006
Create Date: 2026-09-17
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("payroll_code", sa.String(length=50), nullable=True))
    op.create_unique_constraint("uq_users_business_id_payroll_code", "users", ["business_id", "payroll_code"])


def downgrade() -> None:
    op.drop_constraint("uq_users_business_id_payroll_code", "users", type_="unique")
    op.drop_column("users", "payroll_code")
