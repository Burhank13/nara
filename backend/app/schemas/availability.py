import uuid
from datetime import time

from pydantic import BaseModel, Field, model_validator

from app.models.availability import Availability


class AvailabilityDay(BaseModel):
    weekday: int = Field(ge=0, le=6, description="Monday is 0")
    start_time: time
    end_time: time

    @model_validator(mode="after")
    def _end_after_start(self) -> "AvailabilityDay":
        if self.end_time <= self.start_time:
            raise ValueError("end_time must be after start_time")
        return self

    @classmethod
    def of(cls, row: Availability) -> "AvailabilityDay":
        return cls(weekday=row.weekday, start_time=row.start_time, end_time=row.end_time)


class WeekRequest(BaseModel):
    """The whole week, replacing whatever was set before. Days left out mean 'not available'."""

    days: list[AvailabilityDay] = Field(default_factory=list, max_length=7)

    @model_validator(mode="after")
    def _one_window_per_day(self) -> "WeekRequest":
        weekdays = [day.weekday for day in self.days]
        if len(set(weekdays)) != len(weekdays):
            raise ValueError("Each weekday can only appear once")
        return self


class WeekResponse(BaseModel):
    days: list[AvailabilityDay]


class TeamMemberAvailability(BaseModel):
    user_id: uuid.UUID
    full_name: str
    role: str
    days: list[AvailabilityDay]


class TeamAvailabilityResponse(BaseModel):
    members: list[TeamMemberAvailability]
