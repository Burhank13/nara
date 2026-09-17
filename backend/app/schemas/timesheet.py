import uuid
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, StringConstraints

from app.models.shift import Shift
from app.models.user import User
from app.schemas.overview import EmployeeHoursResponse
from app.schemas.shift import ShiftResponse

Reason = Annotated[str, StringConstraints(strip_whitespace=True, min_length=4, max_length=500)]


class EditShiftRequest(BaseModel):
    """Times are the shop's wall clock, so an owner in another state still edits in shop hours.
    Leaving a field out keeps the time it already has."""

    started_at: datetime | None = None
    ended_at: datetime | None = None
    reason: Reason


class TimesheetShift(ShiftResponse):
    user_id: uuid.UUID
    full_name: str

    @classmethod
    def of(cls, shift: Shift, now: datetime | None = None) -> "TimesheetShift":
        return cls(
            **ShiftResponse.of(shift, now).model_dump(),
            user_id=shift.user_id,
            full_name=shift.user.full_name,
        )


class StaffOption(BaseModel):
    user_id: uuid.UUID
    full_name: str

    @classmethod
    def of(cls, user: User) -> "StaffOption":
        return cls(user_id=user.id, full_name=user.full_name)


class TimesheetResponse(BaseModel):
    period: str
    starts_at: datetime
    ends_at: datetime
    total_hours: float
    shift_count: int
    open_count: int
    hours_by_employee: list[EmployeeHoursResponse]
    shifts: list[TimesheetShift]
    staff: list[StaffOption]
