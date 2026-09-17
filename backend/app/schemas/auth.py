import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr

from app.models.business import Business, BusinessStatus
from app.models.user import UserRole, UserStatus
from app.schemas.common import Name, Password, Timezone
from app.services.billing import effective_status, grace_ends_at


class SignupRequest(BaseModel):
    business_name: Name
    full_name: Name
    email: EmailStr
    password: Password
    timezone: Timezone = "Australia/Sydney"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: uuid.UUID
    email: EmailStr
    full_name: str
    role: UserRole
    status: UserStatus
    created_at: datetime

    model_config = {"from_attributes": True}


class BusinessResponse(BaseModel):
    id: uuid.UUID
    name: str
    abn: str | None
    timezone: str
    status: BusinessStatus
    trial_ends_at: datetime | None
    # When the current countdown runs out, whichever countdown is running.
    grace_ends_at: datetime | None
    seat_limit: int

    @classmethod
    def of(cls, business: Business) -> "BusinessResponse":
        return cls(
            id=business.id,
            name=business.name,
            abn=business.abn,
            timezone=business.timezone,
            status=effective_status(business),
            trial_ends_at=business.trial_ends_at,
            grace_ends_at=grace_ends_at(business),
            seat_limit=business.effective_seat_limit,
        )


class SessionResponse(BaseModel):
    user: UserResponse
    business: BusinessResponse


class TokenResponse(SessionResponse):
    access_token: str
    token_type: str = "bearer"
