import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models.user import User, UserStatus


def hash_invite_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def invite_link(raw_token: str) -> str:
    return f"{settings.app_base_url.rstrip('/')}/join/{raw_token}"


def issue_invite(user: User, invited_by: User) -> str:
    """Stamps a fresh invite onto the user and returns the raw token (only ever seen here)."""
    raw_token = secrets.token_urlsafe(32)
    now = datetime.now(UTC)

    user.status = UserStatus.invited
    user.invited_by_id = invited_by.id
    user.invited_at = now
    user.invite_expires_at = now + timedelta(days=settings.invite_expiry_days)
    user.invite_token_hash = hash_invite_token(raw_token)
    return raw_token


def clear_invite(user: User) -> None:
    user.invite_token_hash = None
    user.invite_expires_at = None


def find_pending_invite(db: Session, raw_token: str) -> User | None:
    """Returns the invited user for a token, or None if it is unknown, used or expired."""
    user = db.execute(
        select(User).where(User.invite_token_hash == hash_invite_token(raw_token))
    ).scalar_one_or_none()

    if user is None or user.status != UserStatus.invited:
        return None
    if user.invite_expires_at is None or user.invite_expires_at <= datetime.now(UTC):
        return None
    return user
