import uuid
from datetime import date, datetime
from typing import Annotated

from pydantic import BaseModel, StringConstraints

from app.services.payroll import OpenShift, PayrollLine, PayrollRun

PayrollCode = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=50)]


class UpdateMemberRequest(BaseModel):
    """Null clears the code; leaving it out changes nothing."""

    payroll_code: PayrollCode | None = None


class PayrollLineResponse(BaseModel):
    user_id: uuid.UUID
    full_name: str
    payroll_code: str | None
    work_date: date
    hours: float
    shift_count: int

    @classmethod
    def of(cls, line: PayrollLine) -> "PayrollLineResponse":
        return cls(
            user_id=line.user_id,
            full_name=line.full_name,
            payroll_code=line.payroll_code,
            work_date=line.work_date,
            hours=line.hours,
            shift_count=line.shift_count,
        )


class OpenShiftResponse(BaseModel):
    full_name: str
    started_at: datetime

    @classmethod
    def of(cls, entry: OpenShift) -> "OpenShiftResponse":
        return cls(full_name=entry.full_name, started_at=entry.started_at)


class PayrollResponse(BaseModel):
    period: str
    starts_at: datetime
    ends_at: datetime
    rounding_minutes: int
    total_hours: float
    ready: bool
    lines: list[PayrollLineResponse]
    open_shifts: list[OpenShiftResponse]
    missing_codes: list[str]

    @classmethod
    def of(cls, run: PayrollRun, period: str, starts_at: datetime, ends_at: datetime) -> "PayrollResponse":
        return cls(
            period=period,
            starts_at=starts_at,
            ends_at=ends_at,
            rounding_minutes=run.rounding_minutes,
            total_hours=run.total_hours,
            ready=run.ready,
            lines=[PayrollLineResponse.of(line) for line in run.lines],
            open_shifts=[OpenShiftResponse.of(entry) for entry in run.open_shifts],
            missing_codes=run.missing_codes,
        )
