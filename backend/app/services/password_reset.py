import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models.user import User, UserStatus


def hash_reset_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def reset_link(raw_token: str) -> str:
    return f"{settings.app_base_url.rstrip('/')}/reset/{raw_token}"


def issue_reset(user: User) -> str:
    """Stamps a fresh reset token onto the user and returns the raw one, seen only here."""
    raw_token = secrets.token_urlsafe(32)
    user.reset_token_hash = hash_reset_token(raw_token)
    user.reset_expires_at = datetime.now(UTC) + timedelta(hours=settings.reset_token_hours)
    return raw_token


def clear_reset(user: User) -> None:
    user.reset_token_hash = None
    user.reset_expires_at = None


def find_reset(db: Session, raw_token: str) -> User | None:
    """The user for a live token, or None if it is unknown, already used or expired."""
    user = db.execute(
        select(User).where(User.reset_token_hash == hash_reset_token(raw_token))
    ).scalar_one_or_none()

    if user is None or user.status != UserStatus.active:
        return None
    if user.reset_expires_at is None or user.reset_expires_at <= datetime.now(UTC):
        return None
    return user


def can_reset(user: User | None) -> bool:
    """An invited user has no password yet: their invite is the way in, not a reset."""
    return user is not None and user.status == UserStatus.active and user.password_hash is not None
