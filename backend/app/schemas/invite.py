from datetime import datetime

from pydantic import BaseModel, EmailStr

from app.models.user import UserRole
from app.schemas.common import Name, Password


class InvitePreviewResponse(BaseModel):
    business_name: str
    invited_by: str | None
    email: EmailStr
    full_name: str
    role: UserRole
    expires_at: datetime


class AcceptInviteRequest(BaseModel):
    full_name: Name
    password: Password
