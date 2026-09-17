import uuid
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, EmailStr

from app.models.user import UserRole, UserStatus
from app.schemas.common import Name
from app.services.seats import SeatUsage


class InvitableRole(StrEnum):
    manager = "manager"
    employee = "employee"


class InviteRequest(BaseModel):
    email: EmailStr
    full_name: Name
    role: InvitableRole = InvitableRole.employee


class MemberResponse(BaseModel):
    id: uuid.UUID
    email: EmailStr
    full_name: str
    payroll_code: str | None
    role: UserRole
    status: UserStatus
    invited_at: datetime | None
    invite_expires_at: datetime | None
    accepted_at: datetime | None
    archived_at: datetime | None

    model_config = {"from_attributes": True}


class SeatUsageResponse(BaseModel):
    used: int
    limit: int
    available: int

    @classmethod
    def of(cls, usage: SeatUsage) -> "SeatUsageResponse":
        return cls(used=usage.used, limit=usage.limit, available=usage.available)


class TeamResponse(BaseModel):
    members: list[MemberResponse]
    seats: SeatUsageResponse


class InviteResponse(BaseModel):
    member: MemberResponse
    invite_url: str
    seats: SeatUsageResponse
