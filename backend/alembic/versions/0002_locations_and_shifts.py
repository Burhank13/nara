"""Clock in/out: shop zones and shifts

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-17
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

shift_status = sa.Enum("open", "closed", name="shift_status")


def upgrade() -> None:
    op.create_table(
        "locations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("business_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("address", sa.String(length=500), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("radius_m", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("radius_m BETWEEN 50 AND 300", name="ck_locations_radius_within_bounds"),
        sa.CheckConstraint("latitude BETWEEN -90 AND 90", name="ck_locations_latitude_within_bounds"),
        sa.CheckConstraint("longitude BETWEEN -180 AND 180", name="ck_locations_longitude_within_bounds"),
        sa.ForeignKeyConstraint(
            ["business_id"],
            ["businesses.id"],
            name="fk_locations_business_id_businesses",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_locations"),
    )
    op.create_index("ix_locations_business_id", "locations", ["business_id"])

    op.create_table(
        "shifts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("business_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("location_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", shift_status, nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("start_latitude", sa.Float(), nullable=False),
        sa.Column("start_longitude", sa.Float(), nullable=False),
        sa.Column("start_accuracy_m", sa.Float(), nullable=False),
        sa.Column("start_distance_m", sa.Float(), nullable=False),
        sa.Column("end_latitude", sa.Float(), nullable=True),
        sa.Column("end_longitude", sa.Float(), nullable=True),
        sa.Column("end_accuracy_m", sa.Float(), nullable=True),
        sa.Column("end_distance_m", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["business_id"],
            ["businesses.id"],
            name="fk_shifts_business_id_businesses",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_shifts_user_id_users", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["location_id"], ["locations.id"], name="fk_shifts_location_id_locations", ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_shifts"),
    )
    op.create_index("ix_shifts_user_id", "shifts", ["user_id"])
    op.create_index("ix_shifts_business_id_started_at", "shifts", ["business_id", "started_at"])
    op.create_index(
        "uq_shifts_one_open_per_user",
        "shifts",
        ["user_id"],
        unique=True,
        postgresql_where=sa.text("status = 'open'"),
    )


def downgrade() -> None:
    op.drop_index("uq_shifts_one_open_per_user", table_name="shifts")
    op.drop_index("ix_shifts_business_id_started_at", table_name="shifts")
    op.drop_index("ix_shifts_user_id", table_name="shifts")
    op.drop_table("shifts")
    op.drop_index("ix_locations_business_id", table_name="locations")
    op.drop_table("locations")
    shift_status.drop(op.get_bind(), checkfirst=True)
