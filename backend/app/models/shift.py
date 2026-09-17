import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Index, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.location import Location
    from app.models.user import User


class ShiftStatus(enum.StrEnum):
    open = "open"
    closed = "closed"


shift_status_enum = Enum(
    ShiftStatus,
    name="shift_status",
    values_callable=lambda enum_cls: [member.value for member in enum_cls],
)


class Shift(Base):
    __tablename__ = "shifts"
    __table_args__ = (
        # One open shift per person, enforced by the database rather than by a read-then-write check.
        Index(
            "uq_shifts_one_open_per_user",
            "user_id",
            unique=True,
            postgresql_where=text("status = 'open'"),
        ),
        Index("ix_shifts_business_id_started_at", "business_id", "started_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    location_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("locations.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[ShiftStatus] = mapped_column(shift_status_enum, nullable=False, default=ShiftStatus.open)

    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # What the phone reported at each end of the shift, kept as the record of the check that was made.
    start_latitude: Mapped[float] = mapped_column(Float, nullable=False)
    start_longitude: Mapped[float] = mapped_column(Float, nullable=False)
    start_accuracy_m: Mapped[float] = mapped_column(Float, nullable=False)
    start_distance_m: Mapped[float] = mapped_column(Float, nullable=False)

    end_latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    end_longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    end_accuracy_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    end_distance_m: Mapped[float | None] = mapped_column(Float, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()"), onupdate=text("now()")
    )

    user: Mapped["User"] = relationship()
    location: Mapped["Location | None"] = relationship()
