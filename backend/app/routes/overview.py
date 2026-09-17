from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import require_owner, require_owner_or_manager
from app.models.user import User
from app.schemas.overview import (
    EmployeeHoursResponse,
    LiveBoardResponse,
    LiveShift,
    OverviewResponse,
)
from app.services.reports import business_shifts_in_period, headcount, hours_by_employee, open_shifts
from app.services.shifts import Period, elapsed_hours, period_bounds

router = APIRouter(tags=["overview"])


@router.get("/shifts/live", response_model=LiveBoardResponse)
def live_board(
    current_user: User = Depends(require_owner_or_manager), db: Session = Depends(get_db)
) -> LiveBoardResponse:
    """Who is on shift right now. Managers see this too; the UI polls it every 15 seconds."""
    shifts = open_shifts(db, current_user.business_id)
    return LiveBoardResponse(
        on_shift=[LiveShift.of(shift) for shift in shifts],
        staff_count=headcount(db, current_user.business_id).total,
    )


@router.get("/overview", response_model=OverviewResponse)
def overview(
    period: Period = Period.fortnight,
    current_user: User = Depends(require_owner),
    db: Session = Depends(get_db),
) -> OverviewResponse:
    """The owner's dashboard. Team hours and per-person totals are owner-only."""
    business_id = current_user.business_id
    starts_at, ends_at = period_bounds(current_user.business.timezone, period)

    staff = headcount(db, business_id)
    live = open_shifts(db, business_id)
    shifts = business_shifts_in_period(db, business_id, starts_at, ends_at)
    summaries = hours_by_employee(shifts)
    on_shift = [LiveShift.of(shift) for shift in live]

    return OverviewResponse(
        period=period.value,
        starts_at=starts_at,
        ends_at=ends_at,
        staff_count=staff.total,
        active_count=staff.active,
        invited_count=staff.invited,
        on_shift=on_shift,
        needs_attention=[shift for shift in on_shift if shift.needs_attention],
        team_hours=round(sum(elapsed_hours(shift) for shift in shifts), 2),
        shift_count=len(shifts),
        hours_by_employee=[EmployeeHoursResponse.of(summary) for summary in summaries],
    )
