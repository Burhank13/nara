import uuid
from datetime import UTC, date, datetime, time, timedelta
from enum import StrEnum
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.config import settings
from app.errors import api_error
from app.models.business import Business
from app.models.location import Location
from app.models.shift import Shift, ShiftStatus
from app.models.shift_edit import ShiftEdit
from app.models.user import User
from app.services.billing import is_writable
from app.services.geofence import check_zones, distance_m


class Period(StrEnum):
    week = "week"
    fortnight = "fortnight"
    month = "month"


def active_locations(db: Session, business_id: uuid.UUID) -> list[Location]:
    return list(
        db.execute(
            select(Location)
            .where(Location.business_id == business_id, Location.is_active.is_(True))
            .order_by(Location.name)
        )
        .scalars()
        .all()
    )


def get_open_shift(db: Session, user_id: uuid.UUID) -> Shift | None:
    return db.execute(
        select(Shift).where(Shift.user_id == user_id, Shift.status == ShiftStatus.open)
    ).scalar_one_or_none()


def elapsed_hours(shift: Shift, now: datetime | None = None) -> float:
    end = shift.ended_at or now or datetime.now(UTC)
    return round((end - shift.started_at).total_seconds() / 3600, 2)


def needs_attention(shift: Shift, now: datetime | None = None) -> bool:
    """An open shift running past the flag threshold is almost always a missed clock-out."""
    if shift.status != ShiftStatus.open:
        return False
    return elapsed_hours(shift, now) >= settings.open_shift_flag_hours


def start_shift(
    db: Session, user: User, business: Business, latitude: float, longitude: float, accuracy_m: float
) -> Shift:
    if not is_writable(business):
        raise api_error(
            402,
            "billing_inactive",
            "This business can't start new shifts right now. Ask the owner to check billing.",
        )

    if get_open_shift(db, user.id) is not None:
        raise api_error(409, "shift_already_open", "You already have a shift running. End it first.")

    if accuracy_m > settings.max_gps_accuracy_m:
        raise api_error(
            409,
            "gps_inaccurate",
            "Use your phone for a reliable location check.",
            accuracy_m=round(accuracy_m),
            required_accuracy_m=settings.max_gps_accuracy_m,
        )

    locations = active_locations(db, business.id)
    zone = check_zones(locations, latitude, longitude)
    if zone is None:
        raise api_error(409, "no_zone_configured", "The owner hasn't set up a shop zone yet.")

    if not zone.inside:
        raise api_error(
            409,
            "outside_zone",
            f"You're too far from {zone.location.name} to start a shift.",
            distance_m=round(zone.distance_m),
            radius_m=zone.location.radius_m,
            location_name=zone.location.name,
        )

    shift = Shift(
        business_id=business.id,
        user_id=user.id,
        location_id=zone.location.id,
        status=ShiftStatus.open,
        started_at=datetime.now(UTC),
        start_latitude=latitude,
        start_longitude=longitude,
        start_accuracy_m=accuracy_m,
        start_distance_m=zone.distance_m,
    )
    db.add(shift)
    db.flush()
    db.refresh(shift)
    return shift


def end_shift(
    db: Session,
    user: User,
    latitude: float | None = None,
    longitude: float | None = None,
    accuracy_m: float | None = None,
) -> Shift:
    """Ending always works: no zone check, no billing gate, and location is optional."""
    shift = get_open_shift(db, user.id)
    if shift is None:
        raise api_error(409, "no_open_shift", "You don't have a shift running.")

    shift.status = ShiftStatus.closed
    shift.ended_at = datetime.now(UTC)
    shift.end_latitude = latitude
    shift.end_longitude = longitude
    shift.end_accuracy_m = accuracy_m

    if latitude is not None and longitude is not None and shift.location is not None:
        shift.end_distance_m = distance_m(
            latitude, longitude, shift.location.latitude, shift.location.longitude
        )

    db.flush()
    db.refresh(shift)
    return shift


def period_bounds(timezone: str, period: Period, now: datetime | None = None) -> tuple[datetime, datetime]:
    """Period boundaries in the business's own time zone, returned as UTC instants."""
    tz = ZoneInfo(timezone)
    today = (now or datetime.now(UTC)).astimezone(tz).date()

    if period == Period.week:
        start = today - timedelta(days=today.weekday())
        end = start + timedelta(days=7)
    elif period == Period.fortnight:
        start = today - timedelta(days=today.weekday() + 7)
        end = start + timedelta(days=14)
    else:
        start = today.replace(day=1)
        end = (start + timedelta(days=32)).replace(day=1)

    return _local_midnight(start, tz), _local_midnight(end, tz)


def _local_midnight(day: date, tz: ZoneInfo) -> datetime:
    return datetime.combine(day, time.min, tzinfo=tz).astimezone(UTC)


def shifts_in_period(db: Session, user_id: uuid.UUID, start: datetime, end: datetime) -> list[Shift]:
    return list(
        db.execute(
            select(Shift)
            .options(
                joinedload(Shift.location),
                selectinload(Shift.edits).joinedload(ShiftEdit.edited_by),
            )
            .where(Shift.user_id == user_id, Shift.started_at >= start, Shift.started_at < end)
            .order_by(Shift.started_at.desc())
        )
        .scalars()
        .all()
    )
