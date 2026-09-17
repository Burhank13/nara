import csv
import io
import uuid
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.errors import api_error
from app.models.shift import Shift, ShiftStatus
from app.models.shift_edit import ShiftEdit
from app.models.user import User
from app.services.shifts import elapsed_hours

CSV_COLUMNS = (
    "Employee",
    "Date",
    "Start",
    "End",
    "Hours",
    "Status",
    "Location",
    "Edited",
    "Last edit reason",
)


def timesheet_shifts(
    db: Session,
    business_id: uuid.UUID,
    start: datetime,
    end: datetime,
    user_id: uuid.UUID | None = None,
) -> list[Shift]:
    query = (
        select(Shift)
        .options(
            joinedload(Shift.user),
            joinedload(Shift.location),
            selectinload(Shift.edits).joinedload(ShiftEdit.edited_by),
        )
        .where(Shift.business_id == business_id, Shift.started_at >= start, Shift.started_at < end)
        .order_by(Shift.started_at.desc())
    )
    if user_id is not None:
        query = query.where(Shift.user_id == user_id)
    return list(db.execute(query).scalars().all())


def get_shift_for_business(db: Session, business_id: uuid.UUID, shift_id: uuid.UUID) -> Shift:
    shift = db.execute(
        select(Shift)
        .options(joinedload(Shift.user), joinedload(Shift.location), selectinload(Shift.edits))
        .where(Shift.id == shift_id, Shift.business_id == business_id)
    ).scalar_one_or_none()
    if shift is None:
        raise api_error(404, "shift_not_found", "That shift no longer exists.")
    return shift


def edit_shift(
    db: Session,
    shift: Shift,
    editor: User,
    reason: str,
    started_at: datetime | None = None,
    ended_at: datetime | None = None,
    timezone: str = "UTC",
) -> Shift:
    """Correct a shift's times. `started_at`/`ended_at` are wall-clock times in the business's zone."""
    if started_at is None and ended_at is None:
        raise api_error(400, "nothing_to_change", "Change the start or the end time.")

    tz = ZoneInfo(timezone)
    previous_started_at = shift.started_at
    previous_ended_at = shift.ended_at

    new_started_at = _to_utc(started_at, tz) if started_at else previous_started_at
    new_ended_at = _to_utc(ended_at, tz) if ended_at else previous_ended_at

    now = datetime.now(UTC)
    if new_started_at > now or (new_ended_at is not None and new_ended_at > now):
        raise api_error(409, "future_time", "A shift can't be logged in the future.")
    if new_ended_at is not None and new_ended_at <= new_started_at:
        raise api_error(409, "end_before_start", "The end time has to be after the start time.")

    if new_started_at == previous_started_at and new_ended_at == previous_ended_at:
        raise api_error(400, "nothing_to_change", "Those are already the times on this shift.")

    shift.started_at = new_started_at
    shift.ended_at = new_ended_at
    # Giving an open shift an end time closes it: this is how a missed clock-out gets fixed.
    if new_ended_at is not None:
        shift.status = ShiftStatus.closed

    db.add(
        ShiftEdit(
            shift_id=shift.id,
            edited_by_id=editor.id,
            previous_started_at=previous_started_at,
            previous_ended_at=previous_ended_at,
            new_started_at=new_started_at,
            new_ended_at=new_ended_at,
            reason=reason,
        )
    )
    db.flush()
    db.refresh(shift)
    return shift


def _to_utc(wall_clock: datetime, tz: ZoneInfo) -> datetime:
    if wall_clock.tzinfo is not None:
        raise api_error(
            400, "invalid_request", "Send times as the shop's local clock time, without a time zone."
        )
    return wall_clock.replace(tzinfo=tz).astimezone(UTC)


def to_csv(shifts: list[Shift], timezone: str) -> str:
    tz = ZoneInfo(timezone)
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(CSV_COLUMNS)

    for shift in sorted(shifts, key=lambda row: (row.user.full_name, row.started_at)):
        started = shift.started_at.astimezone(tz)
        ended = shift.ended_at.astimezone(tz) if shift.ended_at else None
        last_edit = shift.edits[-1] if shift.edits else None
        writer.writerow(
            [
                safe_cell(shift.user.full_name),
                started.strftime("%Y-%m-%d"),
                started.strftime("%H:%M"),
                ended.strftime("%H:%M") if ended else "",
                # An open shift has no settled duration, so payroll sees a gap to chase, not a guess.
                f"{elapsed_hours(shift):.2f}" if ended else "",
                shift.status.value,
                safe_cell(shift.location.name if shift.location else ""),
                "yes" if shift.edits else "no",
                safe_cell(last_edit.reason if last_edit else ""),
            ]
        )

    return buffer.getvalue()


def safe_cell(text: str) -> str:
    """Staff names and edit reasons are typed by users; a leading =, +, - or @ makes Excel
    treat the cell as a formula, so it is quoted off."""
    return "'" + text if text[:1] in ("=", "+", "-", "@") else text


def export_filename(business_name: str, start: datetime, end: datetime, timezone: str) -> str:
    tz = ZoneInfo(timezone)
    slug = "".join(char if char.isalnum() else "-" for char in business_name.lower()).strip("-")
    return f"timesheet-{slug}-{start.astimezone(tz):%Y%m%d}-{end.astimezone(tz):%Y%m%d}.csv"
