from datetime import datetime

from pydantic import BaseModel

from app.schemas.common import Abn, Name, Timezone


class UpdateBusinessRequest(BaseModel):
    """Every field is optional: the setup wizard saves one step at a time."""

    name: Name | None = None
    abn: Abn | None = None
    timezone: Timezone | None = None


class OnboardingStep(BaseModel):
    key: str
    title: str
    description: str
    done: bool
    optional: bool = False


class OnboardingResponse(BaseModel):
    steps: list[OnboardingStep]
    complete: bool
    next_step: str | None
    days_left: int | None
    trial_ends_at: datetime | None
    seats_used: int
    seat_limit: int
