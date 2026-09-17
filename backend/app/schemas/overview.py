import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.shift import Shift
from app.services.reports import EmployeeHours
from app.services.shifts import elapsed_hours, needs_attention


class LiveShift(BaseModel):
    shift_id: uuid.UUID
    user_id: uuid.UUID
    full_name: str
    started_at: datetime
    hours: float
    start_distance_m: float
    location_name: str | None
    needs_attention: bool

    @classmethod
    def of(cls, shift: Shift, now: datetime | None = None) -> "LiveShift":
        return cls(
            shift_id=shift.id,
            user_id=shift.user_id,
            full_name=shift.user.full_name,
            started_at=shift.started_at,
            hours=elapsed_hours(shift, now),
            start_distance_m=round(shift.start_distance_m),
            location_name=shift.location.name if shift.location else None,
            needs_attention=needs_attention(shift, now),
        )


class LiveBoardResponse(BaseModel):
    on_shift: list[LiveShift]
    staff_count: int


class EmployeeHoursResponse(BaseModel):
    user_id: uuid.UUID
    full_name: str
    shift_count: int
    hours: float
    flagged: bool

    @classmethod
    def of(cls, summary: EmployeeHours) -> "EmployeeHoursResponse":
        return cls(
            user_id=summary.user_id,
            full_name=summary.full_name,
            shift_count=summary.shift_count,
            hours=summary.hours,
            flagged=summary.flagged,
        )


class OverviewResponse(BaseModel):
    period: str
    starts_at: datetime
    ends_at: datetime

    staff_count: int
    active_count: int
    invited_count: int

    on_shift: list[LiveShift]
    needs_attention: list[LiveShift]

    team_hours: float
    shift_count: int
    hours_by_employee: list[EmployeeHoursResponse]
