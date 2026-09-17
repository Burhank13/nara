import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.shift import Shift
    from app.models.user import User


class ShiftEdit(Base):
    """One row per owner edit of a shift's times. Append-only: rows are never changed or removed."""

    __tablename__ = "shift_edits"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    shift_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("shifts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    edited_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    # Both sides of the change are kept, so the history reads without replaying every row.
    previous_started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    previous_ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    new_started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    new_ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    reason: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

    shift: Mapped["Shift"] = relationship(back_populates="edits")
    edited_by: Mapped["User"] = relationship()
