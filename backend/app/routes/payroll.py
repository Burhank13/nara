from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import require_owner
from app.models.user import User
from app.schemas.payroll import PayrollResponse
from app.services.payroll import PayrollRun, build_run, to_csv
from app.services.shifts import Period, period_bounds
from app.services.timesheets import timesheet_shifts

router = APIRouter(prefix="/payroll", tags=["payroll"])


def _run_for(db: Session, current_user: User, period: Period) -> tuple[PayrollRun, datetime, datetime]:
    business = current_user.business
    starts_at, ends_at = period_bounds(business.timezone, period)
    shifts = timesheet_shifts(db, business.id, starts_at, ends_at)
    return build_run(shifts, business.timezone), starts_at, ends_at


@router.get("", response_model=PayrollResponse)
def payroll(
    period: Period = Period.fortnight,
    current_user: User = Depends(require_owner),
    db: Session = Depends(get_db),
) -> PayrollResponse:
    """What goes to the accountant: one line per person per day, with anything unfinished flagged."""
    run, starts_at, ends_at = _run_for(db, current_user, period)
    return PayrollResponse.of(run, period.value, starts_at, ends_at)


@router.get("/export.csv")
def export_csv(
    period: Period = Period.fortnight,
    current_user: User = Depends(require_owner),
    db: Session = Depends(get_db),
) -> Response:
    tz = ZoneInfo(current_user.business.timezone)
    run, starts_at, ends_at = _run_for(db, current_user, period)
    filename = f"payroll-{starts_at.astimezone(tz):%Y%m%d}-{ends_at.astimezone(tz):%Y%m%d}.csv"

    return Response(
        content=to_csv(run),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
