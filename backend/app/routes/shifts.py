import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, require_owner, require_writable_business
from app.models.business import Business
from app.models.user import User
from app.schemas.shift import (
    CurrentShiftResponse,
    EndShiftRequest,
    ShiftPeriodResponse,
    ShiftResponse,
    StartShiftRequest,
)
from app.schemas.timesheet import EditShiftRequest, TimesheetShift
from app.services.shifts import (
    Period,
    end_shift,
    get_open_shift,
    period_bounds,
    shifts_in_period,
    start_shift,
)
from app.services.timesheets import edit_shift, get_shift_for_business

router = APIRouter(prefix="/shifts", tags=["shifts"])


@router.get("/current", response_model=CurrentShiftResponse)
def current_shift(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> CurrentShiftResponse:
    shift = get_open_shift(db, current_user.id)
    return CurrentShiftResponse(shift=ShiftResponse.of(shift) if shift else None)


@router.post("/start", response_model=ShiftResponse, status_code=201)
def start(
    payload: StartShiftRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ShiftResponse:
    shift = start_shift(
        db,
        current_user,
        current_user.business,
        latitude=payload.latitude,
        longitude=payload.longitude,
        accuracy_m=payload.accuracy_m,
    )
    return ShiftResponse.of(shift)


@router.post("/end", response_model=ShiftResponse)
def end(
    payload: EndShiftRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ShiftResponse:
    shift = end_shift(
        db,
        current_user,
        latitude=payload.latitude,
        longitude=payload.longitude,
        accuracy_m=payload.accuracy_m,
    )
    return ShiftResponse.of(shift)


@router.get("/mine", response_model=ShiftPeriodResponse)
def my_shifts(
    period: Period = Period.week,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ShiftPeriodResponse:
    starts_at, ends_at = period_bounds(current_user.business.timezone, period)
    shifts = shifts_in_period(db, current_user.id, starts_at, ends_at)
    responses = [ShiftResponse.of(shift) for shift in shifts]

    return ShiftPeriodResponse(
        period=period.value,
        starts_at=starts_at,
        ends_at=ends_at,
        total_hours=round(sum(shift.hours for shift in responses), 2),
        shift_count=len(responses),
        shifts=responses,
    )


@router.patch("/{shift_id}", response_model=TimesheetShift)
def edit(
    shift_id: uuid.UUID,
    payload: EditShiftRequest,
    current_user: User = Depends(require_owner),
    business: Business = Depends(require_writable_business),
    db: Session = Depends(get_db),
) -> TimesheetShift:
    """Correcting someone's hours is owner-only and always leaves a reason in the audit log."""
    shift = get_shift_for_business(db, business.id, shift_id)
    edited = edit_shift(
        db,
        shift,
        current_user,
        reason=payload.reason,
        started_at=payload.started_at,
        ended_at=payload.ended_at,
        timezone=business.timezone,
    )
    return TimesheetShift.of(edited)
