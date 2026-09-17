import uuid
from datetime import UTC, datetime, timedelta

import jwt
from fastapi import APIRouter, Cookie, Depends, Response, status
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.deps import get_current_user
from app.errors import api_error
from app.models.business import Business, BusinessStatus
from app.models.user import User, UserRole, UserStatus
from app.schemas.auth import (
    BusinessResponse,
    LoginRequest,
    SessionResponse,
    SignupRequest,
    TokenResponse,
    UserResponse,
)
from app.services.auth import get_user_by_email, get_user_by_id, normalize_email
from app.services.security import REFRESH_TOKEN, decode_token, hash_password, verify_password
from app.services.session import REFRESH_COOKIE, REFRESH_COOKIE_PATH, token_response

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def signup(payload: SignupRequest, response: Response, db: Session = Depends(get_db)) -> TokenResponse:
    """Self-serve owner signup: opens a trialing business and signs the owner straight in."""
    email = normalize_email(payload.email)
    if get_user_by_email(db, email):
        raise api_error(409, "email_taken", "That email already has an account.")

    business = Business(
        name=payload.business_name.strip(),
        timezone=payload.timezone,
        status=BusinessStatus.trialing,
        seat_limit=settings.trial_seat_limit,
        trial_ends_at=datetime.now(UTC) + timedelta(days=settings.trial_days),
    )
    owner = User(
        business=business,
        email=email,
        password_hash=hash_password(payload.password),
        full_name=payload.full_name.strip(),
        role=UserRole.owner,
        status=UserStatus.active,
        accepted_at=datetime.now(UTC),
    )
    db.add(owner)
    db.flush()
    db.refresh(owner)

    return token_response(response, owner, business)


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)) -> TokenResponse:
    user = get_user_by_email(db, payload.email)
    if user is None or user.password_hash is None:
        raise api_error(401, "invalid_credentials", "That email or password is not right.")

    if not verify_password(payload.password, user.password_hash):
        raise api_error(401, "invalid_credentials", "That email or password is not right.")
    if user.status != UserStatus.active:
        raise api_error(403, "account_inactive", "This account is no longer active.")

    return token_response(response, user, user.business)


@router.post("/refresh", response_model=TokenResponse)
def refresh(
    response: Response,
    nara_refresh: str | None = Cookie(default=None),
    db: Session = Depends(get_db),
) -> TokenResponse:
    if not nara_refresh:
        raise api_error(401, "not_authenticated", "Sign in to continue.")

    try:
        payload = decode_token(nara_refresh, REFRESH_TOKEN)
        user_id = uuid.UUID(payload["sub"])
    except (jwt.InvalidTokenError, KeyError, ValueError) as exc:
        raise api_error(401, "invalid_token", "Sign in to continue.") from exc

    user = get_user_by_id(db, user_id)
    if user is None or user.status != UserStatus.active:
        raise api_error(401, "invalid_token", "Sign in to continue.")

    return token_response(response, user, user.business)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response) -> None:
    response.delete_cookie(REFRESH_COOKIE, path=REFRESH_COOKIE_PATH)


@router.get("/me", response_model=SessionResponse)
def me(current_user: User = Depends(get_current_user)) -> SessionResponse:
    return SessionResponse(
        user=UserResponse.model_validate(current_user),
        business=BusinessResponse.of(current_user.business),
    )
