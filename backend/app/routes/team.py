import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.deps import require_owner, require_owner_or_manager, require_writable_business
from app.errors import api_error
from app.models.business import Business
from app.models.user import User, UserRole, UserStatus
from app.schemas.payroll import UpdateMemberRequest
from app.schemas.team import (
    InviteRequest,
    InviteResponse,
    MemberResponse,
    SeatUsageResponse,
    TeamResponse,
)
from app.services.auth import get_user_by_email, normalize_email
from app.services.email import invite_email, send
from app.services.invites import clear_invite, invite_link, issue_invite
from app.services.seats import get_seat_usage, reserve_seat

router = APIRouter(prefix="/team", tags=["team"])


def _get_member(db: Session, business_id: uuid.UUID, user_id: uuid.UUID) -> User:
    member = db.execute(
        select(User).where(User.id == user_id, User.business_id == business_id)
    ).scalar_one_or_none()
    if member is None:
        raise api_error(404, "member_not_found", "That person is not on your team.")
    return member


def _invite_response(
    db: Session, business: Business, member: User, raw_token: str, invited_by: User
) -> InviteResponse:
    db.flush()
    db.refresh(member)
    url = invite_link(raw_token)

    # The link comes back either way: if the email bounces the owner can still hand it over.
    send(
        invite_email(
            to=member.email,
            full_name=member.full_name.split()[0],
            business_name=business.name,
            invited_by=invited_by.full_name,
            url=url,
            days=settings.invite_expiry_days,
        )
    )

    return InviteResponse(
        member=MemberResponse.model_validate(member),
        invite_url=url,
        seats=SeatUsageResponse.of(get_seat_usage(db, business)),
    )


@router.get("", response_model=TeamResponse)
def list_team(
    current_user: User = Depends(require_owner_or_manager),
    db: Session = Depends(get_db),
) -> TeamResponse:
    """Owners manage the team here; managers get the same list read-only."""
    members = (
        db.execute(
            select(User)
            .where(User.business_id == current_user.business_id)
            .order_by(User.role, User.full_name)
        )
        .scalars()
        .all()
    )
    return TeamResponse(
        members=[MemberResponse.model_validate(member) for member in members],
        seats=SeatUsageResponse.of(get_seat_usage(db, current_user.business)),
    )


@router.post("/invites", response_model=InviteResponse, status_code=status.HTTP_201_CREATED)
def create_invite(
    payload: InviteRequest,
    current_user: User = Depends(require_owner),
    _: Business = Depends(require_writable_business),
    db: Session = Depends(get_db),
) -> InviteResponse:
    business = reserve_seat(db, current_user.business_id)
    email = normalize_email(payload.email)
    existing = get_user_by_email(db, email)

    if existing is not None:
        if existing.business_id != business.id or existing.status != UserStatus.archived:
            raise api_error(409, "email_taken", "That email already has an account.")
        # Re-inviting someone who left reuses their row rather than orphaning their shift history.
        member = existing
        member.full_name = payload.full_name.strip()
        member.role = UserRole(payload.role.value)
        member.password_hash = None
        member.accepted_at = None
        member.archived_at = None
    else:
        member = User(
            business_id=business.id,
            email=email,
            full_name=payload.full_name.strip(),
            role=UserRole(payload.role.value),
        )
        db.add(member)

    raw_token = issue_invite(member, current_user)
    return _invite_response(db, business, member, raw_token, current_user)


@router.patch("/members/{user_id}", response_model=MemberResponse)
def update_member(
    user_id: uuid.UUID,
    payload: UpdateMemberRequest,
    current_user: User = Depends(require_owner),
    db: Session = Depends(get_db),
) -> MemberResponse:
    """Sets the code payroll knows this person by, so exported hours land on the right employee."""
    member = _get_member(db, current_user.business_id, user_id)
    code = payload.payroll_code

    if code is not None:
        clash = db.execute(
            select(User).where(
                User.business_id == current_user.business_id,
                User.payroll_code == code,
                User.id != member.id,
            )
        ).scalar_one_or_none()
        if clash is not None:
            raise api_error(409, "payroll_code_taken", f"{clash.full_name} already uses that payroll code.")

    member.payroll_code = code
    db.flush()
    db.refresh(member)
    return MemberResponse.model_validate(member)


@router.post("/members/{user_id}/resend", response_model=InviteResponse)
def resend_invite(
    user_id: uuid.UUID,
    current_user: User = Depends(require_owner),
    _: Business = Depends(require_writable_business),
    db: Session = Depends(get_db),
) -> InviteResponse:
    member = _get_member(db, current_user.business_id, user_id)
    if member.status != UserStatus.invited:
        raise api_error(409, "not_invited", "That person has already joined.")

    invite_still_live = member.invite_expires_at is not None and member.invite_expires_at > datetime.now(UTC)
    # A live invite already holds its seat; only a lapsed one has to reserve again.
    business = current_user.business if invite_still_live else reserve_seat(db, current_user.business_id)

    raw_token = issue_invite(member, current_user)
    return _invite_response(db, business, member, raw_token, current_user)


@router.delete("/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_invite(
    user_id: uuid.UUID,
    current_user: User = Depends(require_owner),
    db: Session = Depends(get_db),
) -> None:
    member = _get_member(db, current_user.business_id, user_id)
    if member.status != UserStatus.invited:
        raise api_error(409, "not_invited", "Archive this person instead of deleting them.")
    db.delete(member)


@router.post("/members/{user_id}/archive", response_model=MemberResponse)
def archive_member(
    user_id: uuid.UUID,
    current_user: User = Depends(require_owner),
    db: Session = Depends(get_db),
) -> MemberResponse:
    member = _get_member(db, current_user.business_id, user_id)
    if member.role == UserRole.owner:
        raise api_error(409, "cannot_archive_owner", "The owner can't be archived.")
    if member.status == UserStatus.archived:
        return MemberResponse.model_validate(member)

    member.status = UserStatus.archived
    member.archived_at = datetime.now(UTC)
    clear_invite(member)
    db.flush()
    db.refresh(member)
    return MemberResponse.model_validate(member)


@router.post("/members/{user_id}/restore", response_model=MemberResponse)
def restore_member(
    user_id: uuid.UUID,
    current_user: User = Depends(require_owner),
    _: Business = Depends(require_writable_business),
    db: Session = Depends(get_db),
) -> MemberResponse:
    member = _get_member(db, current_user.business_id, user_id)
    if member.status != UserStatus.archived:
        raise api_error(409, "not_archived", "That person is already on the team.")
    if member.accepted_at is None:
        raise api_error(409, "never_joined", "This person never joined. Invite them again instead.")

    reserve_seat(db, current_user.business_id)
    member.status = UserStatus.active
    member.archived_at = None
    db.flush()
    db.refresh(member)
    return MemberResponse.model_validate(member)


@router.get("/seats", response_model=SeatUsageResponse)
def seats(current_user: User = Depends(require_owner), db: Session = Depends(get_db)) -> SeatUsageResponse:
    return SeatUsageResponse.of(get_seat_usage(db, current_user.business))
