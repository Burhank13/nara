import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, Enum, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.user import User


class BusinessStatus(enum.StrEnum):
    trialing = "trialing"
    active = "active"
    # A failed payment, not a closed account: the shop keeps working through the grace period.
    past_due = "past_due"
    read_only = "read_only"
    suspended = "suspended"
    cancelled = "cancelled"


business_status_enum = Enum(
    BusinessStatus,
    name="business_status",
    values_callable=lambda enum_cls: [member.value for member in enum_cls],
)


class Business(Base):
    __tablename__ = "businesses"
    __table_args__ = (
        CheckConstraint("seat_limit >= 0", name="seat_limit_non_negative"),
        CheckConstraint(
            "seat_limit_override IS NULL OR seat_limit_override >= 0",
            name="seat_limit_override_non_negative",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    abn: Mapped[str | None] = mapped_column(String(20), nullable=True)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="Australia/Sydney")
    status: Mapped[BusinessStatus] = mapped_column(
        business_status_enum, nullable=False, default=BusinessStatus.trialing
    )
    seat_limit: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    seat_limit_override: Mapped[int | None] = mapped_column(Integer, nullable=True)
    trial_ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    past_due_since: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    stripe_customer_id: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True)
    stripe_subscription_id: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    users: Mapped[list["User"]] = relationship(back_populates="business")

    @property
    def effective_seat_limit(self) -> int:
        return self.seat_limit if self.seat_limit_override is None else self.seat_limit_override
