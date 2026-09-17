import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.models.shift import Shift, ShiftStatus
from app.models.user import User, UserRole, UserStatus
from app.services.shifts import elapsed_hours, needs_attention


@dataclass(frozen=True)
class Headcount:
    active: int
    invited: int

    @property
    def total(self) -> int:
        return self.active + self.invited


@dataclass(frozen=True)
class EmployeeHours:
    user_id: uuid.UUID
    full_name: str
    shift_count: int
    hours: float
    flagged: bool


def headcount(db: Session, business_id: uuid.UUID) -> Headcount:
    """Staff the owner is paying for: the owner themselves is not counted."""
    now = datetime.now(UTC)
    rows = db.execute(
        select(User.status, func.count())
        .where(
            User.business_id == business_id,
            User.role != UserRole.owner,
            or_(
                User.status == UserStatus.active,
                and_(User.status == UserStatus.invited, User.invite_expires_at > now),
            ),
        )
        .group_by(User.status)
    ).all()
    counts = dict(rows)
    return Headcount(active=counts.get(UserStatus.active, 0), invited=counts.get(UserStatus.invited, 0))


def active_members(db: Session, business_id: uuid.UUID) -> list[User]:
    """Everyone who can appear on a timesheet, the owner included."""
    return list(
        db.execute(
            select(User)
            .where(User.business_id == business_id, User.status == UserStatus.active)
            .order_by(User.full_name)
        )
        .scalars()
        .all()
    )


def open_shifts(db: Session, business_id: uuid.UUID) -> list[Shift]:
    return list(
        db.execute(
            select(Shift)
            .options(joinedload(Shift.user), joinedload(Shift.location))
            .where(Shift.business_id == business_id, Shift.status == ShiftStatus.open)
            .order_by(Shift.started_at)
        )
        .scalars()
        .all()
    )


def business_shifts_in_period(
    db: Session, business_id: uuid.UUID, start: datetime, end: datetime
) -> list[Shift]:
    return list(
        db.execute(
            select(Shift)
            .options(joinedload(Shift.user))
            .where(
                Shift.business_id == business_id,
                Shift.started_at >= start,
                Shift.started_at < end,
            )
            .order_by(Shift.started_at.desc())
        )
        .scalars()
        .all()
    )


def hours_by_employee(shifts: list[Shift], now: datetime | None = None) -> list[EmployeeHours]:
    """Totals per person, highest first. Open shifts count the time run so far."""
    totals: dict[uuid.UUID, list[Shift]] = defaultdict(list)
    for shift in shifts:
        totals[shift.user_id].append(shift)

    summaries = [
        EmployeeHours(
            user_id=user_id,
            full_name=owned[0].user.full_name,
            shift_count=len(owned),
            hours=round(sum(elapsed_hours(shift, now) for shift in owned), 2),
            flagged=any(needs_attention(shift, now) for shift in owned),
        )
        for user_id, owned in totals.items()
    ]
    return sorted(summaries, key=lambda summary: summary.hours, reverse=True)
