from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.config import settings
from app.errors import api_error
from app.models.user import User


def is_locked(user: User, now: datetime | None = None) -> bool:
    return user.locked_until is not None and user.locked_until > (now or datetime.now(UTC))


def assert_not_locked(user: User) -> None:
    """Throttling lives on the user row, so it holds across restarts and every worker process."""
    if is_locked(user):
        raise api_error(
            429,
            "too_many_attempts",
            "Too many sign-in attempts. Try again in a few minutes.",
        )


def record_failure(db: Session, user: User) -> None:
    user.failed_login_count += 1
    if user.failed_login_count >= settings.max_failed_logins:
        user.locked_until = datetime.now(UTC) + timedelta(minutes=settings.lockout_minutes)
        user.failed_login_count = 0
    # Committed here rather than by the request: the caller raises 401 next, and a rolled-back
    # count would let an attacker guess for ever.
    db.commit()


def record_success(db: Session, user: User) -> None:
    user.failed_login_count = 0
    user.locked_until = None
    db.flush()


def revoke_sessions(db: Session, user: User) -> None:
    """Signing out invalidates every token already issued, not just the cookie in this browser."""
    user.token_version += 1
    db.flush()
