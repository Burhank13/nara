from typing import Annotated
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import AfterValidator, Field

from app.services.security import password_too_long


def _check_password(value: str) -> str:
    if password_too_long(value):
        raise ValueError("Password is too long (72 bytes maximum)")
    return value


def _check_timezone(value: str) -> str:
    try:
        ZoneInfo(value)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise ValueError(f"Unknown time zone: {value}") from exc
    return value


Password = Annotated[str, Field(min_length=10, max_length=128), AfterValidator(_check_password)]
Timezone = Annotated[str, Field(max_length=64), AfterValidator(_check_timezone)]
Name = Annotated[str, Field(min_length=1, max_length=255)]
