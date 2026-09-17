import uuid
from collections.abc import Callable

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.errors import api_error
from app.models.business import Business
from app.models.user import User, UserRole, UserStatus
from app.services.auth import get_user_by_id
from app.services.billing import effective_status, is_writable
from app.services.security import ACCESS_TOKEN, decode_token

security = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise api_error(401, "not_authenticated", "Sign in to continue.")

    try:
        payload = decode_token(credentials.credentials, ACCESS_TOKEN)
        user_id = uuid.UUID(payload["sub"])
    except jwt.ExpiredSignatureError as exc:
        raise api_error(401, "token_expired", "Your session has expired. Sign in again.") from exc
    except (jwt.InvalidTokenError, KeyError, ValueError) as exc:
        raise api_error(401, "invalid_token", "Sign in to continue.") from exc

    user = get_user_by_id(db, user_id)
    if user is None:
        raise api_error(401, "invalid_token", "Sign in to continue.")
    if user.status != UserStatus.active:
        raise api_error(403, "account_inactive", "This account is no longer active.")
    return user


def get_current_business(current_user: User = Depends(get_current_user)) -> Business:
    return current_user.business


def require_roles(*roles: UserRole) -> Callable[[User], User]:
    def dependency(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise api_error(403, "forbidden", "You don't have access to this.")
        return current_user

    return dependency


require_owner = require_roles(UserRole.owner)
require_owner_or_manager = require_roles(UserRole.owner, UserRole.manager)


def require_writable_business(business: Business = Depends(get_current_business)) -> Business:
    """Read-only, suspended and cancelled businesses can look but not change anything."""
    if not is_writable(business):
        raise api_error(
            402,
            "billing_inactive",
            f"This business is {effective_status(business).value.replace('_', ' ')}. "
            "Add a payment method to make changes again.",
        )
    return business
