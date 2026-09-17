import uuid

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import require_owner
from app.models.shift import ShiftStatus
from app.models.user import User
from app.schemas.overview import EmployeeHoursResponse
from app.schemas.timesheet import StaffOption, TimesheetResponse, TimesheetShift
from app.services.reports import active_members, hours_by_employee
from app.services.shifts import Period, elapsed_hours, period_bounds
from app.services.timesheets import export_filename, timesheet_shifts, to_csv

router = APIRouter(prefix="/timesheets", tags=["timesheets"])


@router.get("", response_model=TimesheetResponse)
def timesheet(
    period: Period = Period.fortnight,
    user_id: uuid.UUID | None = None,
    current_user: User = Depends(require_owner),
    db: Session = Depends(get_db),
) -> TimesheetResponse:
    """Every shift in the period, with the audit trail attached. Owner only."""
    starts_at, ends_at = period_bounds(current_user.business.timezone, period)
    shifts = timesheet_shifts(db, current_user.business_id, starts_at, ends_at, user_id)

    return TimesheetResponse(
        period=period.value,
        starts_at=starts_at,
        ends_at=ends_at,
        total_hours=round(sum(elapsed_hours(shift) for shift in shifts), 2),
        shift_count=len(shifts),
        open_count=sum(1 for shift in shifts if shift.status == ShiftStatus.open),
        hours_by_employee=[EmployeeHoursResponse.of(row) for row in hours_by_employee(shifts)],
        shifts=[TimesheetShift.of(shift) for shift in shifts],
        staff=[StaffOption.of(member) for member in active_members(db, current_user.business_id)],
    )


@router.get("/export.csv")
def export_csv(
    period: Period = Period.fortnight,
    user_id: uuid.UUID | None = None,
    current_user: User = Depends(require_owner),
    db: Session = Depends(get_db),
) -> Response:
    """Export stays available on a read-only business: an owner can always get their data out."""
    business = current_user.business
    starts_at, ends_at = period_bounds(business.timezone, period)
    shifts = timesheet_shifts(db, business.id, starts_at, ends_at, user_id)
    filename = export_filename(business.name, starts_at, ends_at, business.timezone)

    return Response(
        content=to_csv(shifts, business.timezone),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
