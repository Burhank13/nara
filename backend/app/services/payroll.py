import csv
import io
import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from zoneinfo import ZoneInfo

from app.config import settings
from app.models.shift import Shift, ShiftStatus
from app.services.timesheets import safe_cell

CSV_COLUMNS = ("Payroll code", "Employee", "Date", "Hours")


@dataclass(frozen=True)
class PayrollLine:
    user_id: uuid.UUID
    full_name: str
    payroll_code: str | None
    work_date: date
    hours: float
    shift_count: int


@dataclass(frozen=True)
class OpenShift:
    full_name: str
    started_at: datetime


@dataclass(frozen=True)
class PayrollRun:
    lines: list[PayrollLine]
    total_hours: float
    open_shifts: list[OpenShift]
    missing_codes: list[str]
    rounding_minutes: int

    @property
    def ready(self) -> bool:
        """An unfinished shift has no duration to pay, so the run is held until it is closed."""
        return not self.open_shifts


def round_hours(hours: float, increment_minutes: int) -> float:
    """Half-up, not banker's rounding: these are wages, and 7.125 h has to land on 7.25."""
    if increment_minutes <= 0:
        return float(Decimal(str(hours)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))

    step = Decimal(increment_minutes) / Decimal(60)
    steps = (Decimal(str(hours)) / step).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return float((steps * step).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def build_run(shifts: list[Shift], timezone: str, rounding_minutes: int | None = None) -> PayrollRun:
    increment = settings.payroll_rounding_minutes if rounding_minutes is None else rounding_minutes
    tz = ZoneInfo(timezone)

    worked: dict[tuple[uuid.UUID, date], timedelta] = defaultdict(timedelta)
    counts: dict[tuple[uuid.UUID, date], int] = defaultdict(int)
    people: dict[uuid.UUID, Shift] = {}
    open_shifts: list[OpenShift] = []

    for shift in shifts:
        people[shift.user_id] = shift
        if shift.status == ShiftStatus.open or shift.ended_at is None:
            open_shifts.append(OpenShift(full_name=shift.user.full_name, started_at=shift.started_at))
            continue

        # A shift that runs past midnight is paid against the day it started, as rosters read.
        key = (shift.user_id, shift.started_at.astimezone(tz).date())
        worked[key] += shift.ended_at - shift.started_at
        counts[key] += 1

    lines = [
        PayrollLine(
            user_id=user_id,
            full_name=people[user_id].user.full_name,
            payroll_code=people[user_id].user.payroll_code,
            work_date=work_date,
            # Summed in full and rounded once, so rounding each shift can't drift the day's total.
            hours=round_hours(total.total_seconds() / 3600, increment),
            shift_count=counts[(user_id, work_date)],
        )
        for (user_id, work_date), total in worked.items()
    ]
    lines.sort(key=lambda line: (line.full_name, line.work_date))

    return PayrollRun(
        lines=lines,
        total_hours=round(sum(line.hours for line in lines), 2),
        open_shifts=sorted(open_shifts, key=lambda entry: entry.started_at),
        missing_codes=sorted(
            {shift.user.full_name for shift in people.values() if not shift.user.payroll_code}
        ),
        rounding_minutes=increment,
    )


def to_csv(run: PayrollRun) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(CSV_COLUMNS)

    for line in run.lines:
        writer.writerow(
            [
                safe_cell(line.payroll_code or ""),
                safe_cell(line.full_name),
                line.work_date.isoformat(),
                f"{line.hours:.2f}",
            ]
        )

    return buffer.getvalue()
