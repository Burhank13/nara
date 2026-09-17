from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.errors import api_error
from app.models.user import User, UserStatus
from app.schemas.auth import TokenResponse
from app.schemas.invite import AcceptInviteRequest, InvitePreviewResponse
from app.services.invites import clear_invite, find_pending_invite
from app.services.security import hash_password
from app.services.session import token_response

router = APIRouter(prefix="/invites", tags=["invites"])


def _pending_invite(db: Session, token: str) -> User:
    member = find_pending_invite(db, token)
    if member is None:
        raise api_error(404, "invalid_invite", "This invite link is no longer valid. Ask for a new one.")
    return member


@router.get("/{token}", response_model=InvitePreviewResponse)
def preview_invite(token: str, db: Session = Depends(get_db)) -> InvitePreviewResponse:
    member = _pending_invite(db, token)
    inviter = db.get(User, member.invited_by_id) if member.invited_by_id else None
    return InvitePreviewResponse(
        business_name=member.business.name,
        invited_by=inviter.full_name if inviter else None,
        email=member.email,
        full_name=member.full_name,
        role=member.role,
        expires_at=member.invite_expires_at,
    )


@router.post("/{token}/accept", response_model=TokenResponse)
def accept_invite(
    token: str,
    payload: AcceptInviteRequest,
    response: Response,
    db: Session = Depends(get_db),
) -> TokenResponse:
    member = _pending_invite(db, token)

    member.full_name = payload.full_name.strip()
    member.password_hash = hash_password(payload.password)
    member.status = UserStatus.active
    member.accepted_at = datetime.now(UTC)
    clear_invite(member)
    db.flush()
    db.refresh(member)

    return token_response(response, member, member.business)
