import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.errors import api_error
from app.models.business import Business
from app.models.user import User, UserRole, UserStatus
from app.services.billing import effective_status, is_writable


@dataclass(frozen=True)
class SeatUsage:
    used: int
    limit: int

    @property
    def available(self) -> int:
        return max(self.limit - self.used, 0)

    @property
    def at_limit(self) -> bool:
        return self.used >= self.limit


def count_seats_in_use(db: Session, business_id: uuid.UUID) -> int:
    """A seat is an active employee/manager, or an invite that hasn't expired. Owners are free."""
    now = datetime.now(UTC)
    return db.scalar(
        select(func.count())
        .select_from(User)
        .where(
            User.business_id == business_id,
            User.role != UserRole.owner,
            or_(
                User.status == UserStatus.active,
                and_(User.status == UserStatus.invited, User.invite_expires_at > now),
            ),
        )
    )


def get_seat_usage(db: Session, business: Business) -> SeatUsage:
    return SeatUsage(used=count_seats_in_use(db, business.id), limit=business.effective_seat_limit)


def reserve_seat(db: Session, business_id: uuid.UUID) -> Business:
    """Locks the business row, then counts seats, so concurrent invites can't overshoot the limit.

    The lock is held until the request's transaction commits, which is when the seat is actually taken.
    """
    business = db.execute(select(Business).where(Business.id == business_id).with_for_update()).scalar_one()

    if not is_writable(business):
        raise api_error(
            402,
            "billing_inactive",
            f"This business is {effective_status(business).value.replace('_', ' ')}. "
            "Add a payment method to add people again.",
        )

    usage = get_seat_usage(db, business)
    if usage.at_limit:
        raise api_error(
            409,
            "seat_limit_reached",
            f"All {usage.limit} seats are in use. Add seats to invite someone else.",
        )
    return business
