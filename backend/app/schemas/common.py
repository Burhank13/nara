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


ABN_WEIGHTS = (10, 1, 3, 5, 7, 9, 11, 13, 15, 17, 19)


def _check_abn(value: str) -> str:
    """An ABN carries its own checksum, so a typo is caught here rather than on an invoice."""
    digits = value.replace(" ", "")
    if len(digits) != len(ABN_WEIGHTS) or not digits.isdigit():
        raise ValueError("An ABN is 11 digits")

    weighted = [int(digit) for digit in digits]
    weighted[0] -= 1
    if sum(digit * weight for digit, weight in zip(weighted, ABN_WEIGHTS, strict=True)) % 89 != 0:
        raise ValueError("That ABN doesn't look right. Check the digits.")
    return digits


Password = Annotated[str, Field(min_length=10, max_length=128), AfterValidator(_check_password)]
Abn = Annotated[str, AfterValidator(_check_abn)]
Timezone = Annotated[str, Field(max_length=64), AfterValidator(_check_timezone)]
Name = Annotated[str, Field(min_length=1, max_length=255)]
