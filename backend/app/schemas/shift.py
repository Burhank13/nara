import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.shift import Shift, ShiftStatus
from app.models.shift_edit import ShiftEdit
from app.services.shifts import elapsed_hours, needs_attention


class StartShiftRequest(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    accuracy_m: float = Field(ge=0)


class ShiftEditEntry(BaseModel):
    """Shown to the employee as well as the owner: nobody's hours change without them seeing why."""

    id: uuid.UUID
    edited_by: str
    reason: str
    created_at: datetime
    previous_started_at: datetime
    previous_ended_at: datetime | None
    new_started_at: datetime
    new_ended_at: datetime | None

    @classmethod
    def of(cls, edit: ShiftEdit) -> "ShiftEditEntry":
        return cls(
            id=edit.id,
            edited_by=edit.edited_by.full_name,
            reason=edit.reason,
            created_at=edit.created_at,
            previous_started_at=edit.previous_started_at,
            previous_ended_at=edit.previous_ended_at,
            new_started_at=edit.new_started_at,
            new_ended_at=edit.new_ended_at,
        )


class EndShiftRequest(BaseModel):
    """Location is optional: a denied permission must never trap someone in an open shift."""

    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    accuracy_m: float | None = Field(default=None, ge=0)


class ShiftResponse(BaseModel):
    id: uuid.UUID
    status: ShiftStatus
    started_at: datetime
    ended_at: datetime | None
    hours: float
    location_id: uuid.UUID | None
    location_name: str | None
    start_distance_m: float
    start_accuracy_m: float
    end_distance_m: float | None
    end_accuracy_m: float | None
    needs_attention: bool
    edits: list[ShiftEditEntry]

    @classmethod
    def of(cls, shift: Shift, now: datetime | None = None) -> "ShiftResponse":
        return cls(
            id=shift.id,
            status=shift.status,
            started_at=shift.started_at,
            ended_at=shift.ended_at,
            hours=elapsed_hours(shift, now),
            location_id=shift.location_id,
            location_name=shift.location.name if shift.location else None,
            start_distance_m=round(shift.start_distance_m),
            start_accuracy_m=round(shift.start_accuracy_m),
            end_distance_m=round(shift.end_distance_m) if shift.end_distance_m is not None else None,
            end_accuracy_m=round(shift.end_accuracy_m) if shift.end_accuracy_m is not None else None,
            needs_attention=needs_attention(shift, now),
            edits=[ShiftEditEntry.of(edit) for edit in shift.edits],
        )


class CurrentShiftResponse(BaseModel):
    shift: ShiftResponse | None


class ShiftPeriodResponse(BaseModel):
    period: str
    starts_at: datetime
    ends_at: datetime
    total_hours: float
    shift_count: int
    shifts: list[ShiftResponse]
