from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
import jwt

from app.config import settings
from app.models.user import User

ACCESS_TOKEN = "access"
REFRESH_TOKEN = "refresh"

# bcrypt silently ignores anything past 72 bytes, so longer passwords are rejected at the edge.
BCRYPT_MAX_BYTES = 72


def password_too_long(password: str) -> bool:
    return len(password.encode("utf-8")) > BCRYPT_MAX_BYTES


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str | None) -> bool:
    if not password_hash:
        return False
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def _create_token(user: User, token_type: str, lifetime: timedelta) -> str:
    issued_at = datetime.now(UTC)
    payload = {
        "sub": str(user.id),
        "bid": str(user.business_id),
        "role": user.role.value,
        "typ": token_type,
        # Signing the session generation in is what lets a sign-out invalidate a stolen token.
        "tv": user.token_version,
        "iat": issued_at,
        "exp": issued_at + lifetime,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_access_token(user: User) -> str:
    return _create_token(user, ACCESS_TOKEN, timedelta(minutes=settings.access_token_minutes))


def create_refresh_token(user: User) -> str:
    return _create_token(user, REFRESH_TOKEN, timedelta(days=settings.refresh_token_days))


def decode_token(token: str, expected_type: str) -> dict[str, Any]:
    """Raises jwt.InvalidTokenError (or a subclass) when the token is unusable."""
    payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    if payload.get("typ") != expected_type:
        raise jwt.InvalidTokenError(f"Expected a {expected_type} token")
    return payload
