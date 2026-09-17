from fastapi import APIRouter, Depends
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, require_owner_or_manager
from app.models.availability import Availability
from app.models.user import User, UserRole, UserStatus
from app.schemas.availability import (
    AvailabilityDay,
    TeamAvailabilityResponse,
    TeamMemberAvailability,
    WeekRequest,
    WeekResponse,
)

router = APIRouter(prefix="/availability", tags=["availability"])


def _week_for(db: Session, user_id) -> list[Availability]:
    return list(
        db.execute(select(Availability).where(Availability.user_id == user_id).order_by(Availability.weekday))
        .scalars()
        .all()
    )


@router.get("/mine", response_model=WeekResponse)
def my_availability(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> WeekResponse:
    return WeekResponse(days=[AvailabilityDay.of(row) for row in _week_for(db, current_user.id)])


@router.put("/mine", response_model=WeekResponse)
def set_my_availability(
    payload: WeekRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WeekResponse:
    """Replaces the whole week in one go, so the grid can never end up half-saved."""
    db.execute(delete(Availability).where(Availability.user_id == current_user.id))
    for day in payload.days:
        db.add(
            Availability(
                user_id=current_user.id,
                weekday=day.weekday,
                start_time=day.start_time,
                end_time=day.end_time,
            )
        )
    db.flush()
    return WeekResponse(days=[AvailabilityDay.of(row) for row in _week_for(db, current_user.id)])


@router.get("/team", response_model=TeamAvailabilityResponse)
def team_availability(
    current_user: User = Depends(require_owner_or_manager), db: Session = Depends(get_db)
) -> TeamAvailabilityResponse:
    """The owner's weekly grid. Managers can read it too, but can't change anyone's hours."""
    members = (
        db.execute(
            select(User)
            .where(
                User.business_id == current_user.business_id,
                User.status == UserStatus.active,
                User.role != UserRole.owner,
            )
            .order_by(User.full_name)
        )
        .scalars()
        .all()
    )

    rows = (
        db.execute(
            select(Availability)
            .where(Availability.user_id.in_([member.id for member in members]))
            .order_by(Availability.weekday)
        )
        .scalars()
        .all()
        if members
        else []
    )

    by_user: dict = {}
    for row in rows:
        by_user.setdefault(row.user_id, []).append(AvailabilityDay.of(row))

    return TeamAvailabilityResponse(
        members=[
            TeamMemberAvailability(
                user_id=member.id,
                full_name=member.full_name,
                role=member.role.value,
                days=by_user.get(member.id, []),
            )
            for member in members
        ]
    )
