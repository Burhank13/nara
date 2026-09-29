from typing import Literal, cast

from fastapi import Response

from app.config import settings
from app.models.business import Business
from app.models.user import User
from app.schemas.auth import BusinessResponse, TokenResponse, UserResponse
from app.services.security import create_access_token, create_refresh_token

REFRESH_COOKIE = "maf_refresh"
# Scoped to the auth endpoints so the cookie is not attached to every other API call.
REFRESH_COOKIE_PATH = "/api/auth"


def set_refresh_cookie(response: Response, user: User) -> None:
    response.set_cookie(
        REFRESH_COOKIE,
        create_refresh_token(user),
        max_age=settings.refresh_token_days * 24 * 60 * 60,
        httponly=True,
        secure=settings.cookies_secure,
        samesite=cast(Literal["lax", "strict", "none"], settings.cookie_samesite),
        path=REFRESH_COOKIE_PATH,
    )


def token_response(response: Response, user: User, business: Business) -> TokenResponse:
    set_refresh_cookie(response, user)
    return TokenResponse(
        access_token=create_access_token(user),
        user=UserResponse.model_validate(user),
        business=BusinessResponse.of(business),
    )
