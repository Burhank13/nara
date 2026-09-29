"""Demo data: `python -m app.seed`.

Also runs on boot of the hosted demo when SEED_DEMO_DATA is set, which is why it has to be
safe to run twice. A brand new empty business demonstrates nothing, so this builds a fortnight
of worked shifts, an edit with its audit trail, and payroll codes ready to export.
"""

import random
from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo

from app.config import settings
from app.database import SessionLocal
from app.models.business import Business, BusinessStatus
from app.models.location import Location
from app.models.shift import Shift, ShiftStatus
from app.models.shift_edit import ShiftEdit
from app.models.user import User, UserRole, UserStatus
from app.services.auth import get_user_by_email
from app.services.invites import invite_link, issue_invite
from app.services.security import hash_password

DEMO_PASSWORD = "mafdemo123"
OWNER_EMAIL = "owner@carwash.demo"
MANAGER_EMAIL = "manager@carwash.demo"
EMPLOYEE_EMAIL = "employee@carwash.demo"
INVITED_EMAIL = "newstarter@carwash.demo"

TIMEZONE = "Australia/Sydney"
# Darling Harbour. Somewhere recognisable, so the zone means something on a map.
SHOP_LAT, SHOP_LNG = -33.87365, 151.19956
SHOP_RADIUS_M = 150


def _worked_shift(
    business: Business, user: User, zone: Location, day: datetime, start: time, hours: float
) -> Shift:
    """One finished shift, clocked in at the shop and out again."""
    tz = ZoneInfo(TIMEZONE)
    started = datetime.combine(day.date(), start, tzinfo=tz)
    ended = started + timedelta(hours=hours)
    # A few metres of wander, the way a real fix looks.
    drift = random.uniform(5, 45)

    return Shift(
        business_id=business.id,
        user_id=user.id,
        location_id=zone.id,
        status=ShiftStatus.closed,
        started_at=started.astimezone(UTC),
        ended_at=ended.astimezone(UTC),
        start_latitude=SHOP_LAT,
        start_longitude=SHOP_LNG,
        start_accuracy_m=random.uniform(6, 18),
        start_distance_m=drift,
        end_latitude=SHOP_LAT,
        end_longitude=SHOP_LNG,
        end_accuracy_m=random.uniform(6, 18),
        end_distance_m=drift + random.uniform(0, 20),
    )


def _history(db, business: Business, zone: Location, staff: list[User]) -> Shift:
    """A fortnight of shifts behind everyone, so the timesheet and payroll screens have content.

    Returns one shift to be edited afterwards — the audit trail is the part worth showing, and
    it needs a shift that already exists.
    """
    random.seed(f"{business.id}")  # same demo every rebuild
    tz = ZoneInfo(TIMEZONE)
    today = datetime.now(tz)
    pattern = {
        0: (time(7, 30), 7.5),
        1: (time(8, 0), 6.0),
        2: (time(7, 30), 7.5),
        3: (time(9, 0), 5.5),
        4: (time(7, 30), 8.0),
        5: (time(8, 30), 6.5),
    }

    created: list[Shift] = []
    for days_ago in range(14, 0, -1):
        day = today - timedelta(days=days_ago)
        shape = pattern.get(day.weekday())
        if shape is None:  # Sunday, shop closed
            continue
        for person in staff:
            # Nobody works every single day.
            if random.random() < 0.25:
                continue
            start, hours = shape
            shift = _worked_shift(business, person, zone, day, start, hours)
            db.add(shift)
            created.append(shift)

    db.flush()
    return created[-1]


def _edited(db, shift: Shift, owner: User) -> None:
    """Someone forgot to clock in and the owner fixed it, with the reason on the record."""
    previous_started = shift.started_at
    corrected = previous_started - timedelta(minutes=35)

    db.add(
        ShiftEdit(
            shift_id=shift.id,
            edited_by_id=owner.id,
            previous_started_at=previous_started,
            previous_ended_at=shift.ended_at,
            new_started_at=corrected,
            new_ended_at=shift.ended_at,
            reason="Started at 7:30 but the app was not opened until after the first car.",
        )
    )
    shift.started_at = corrected


def seed() -> None:
    db = SessionLocal()
    try:
        existing = get_user_by_email(db, OWNER_EMAIL)
        if existing:
            # Re-seeding resets the demo passwords. Skipping instead would let DEMO_PASSWORD
            # drift from the hashes already in the database, and sign-in would fail with
            # credentials that look correct in the source.
            reset = (
                db.query(User)
                .filter(User.business_id == existing.business_id, User.password_hash.isnot(None))
                .all()
            )
            for member in reset:
                member.password_hash = hash_password(DEMO_PASSWORD)
            db.commit()
            print(f"Demo business already seeded; reset {len(reset)} passwords.")
            print(f"  sign in with any demo account / {DEMO_PASSWORD}")
            return

        business = Business(
            name="Sparkle Car Wash",
            timezone="Australia/Sydney",
            status=BusinessStatus.trialing,
            seat_limit=settings.trial_seat_limit,
            trial_ends_at=datetime.now(UTC) + timedelta(days=settings.trial_days),
        )
        owner = User(
            business=business,
            email=OWNER_EMAIL,
            password_hash=hash_password(DEMO_PASSWORD),
            full_name="Olivia Owner",
            role=UserRole.owner,
            status=UserStatus.active,
            accepted_at=datetime.now(UTC),
        )
        db.add(owner)

        staff = []
        for email, name, role, code in (
            (MANAGER_EMAIL, "Marco Manager", UserRole.manager, "EMP002"),
            (EMPLOYEE_EMAIL, "Eli Employee", UserRole.employee, "EMP003"),
        ):
            member = User(
                business=business,
                email=email,
                password_hash=hash_password(DEMO_PASSWORD),
                full_name=name,
                role=role,
                status=UserStatus.active,
                accepted_at=datetime.now(UTC),
                # Set already, so the payroll export is ready rather than complaining.
                payroll_code=code,
            )
            db.add(member)
            staff.append(member)

        pending = User(
            business=business,
            email=INVITED_EMAIL,
            full_name="Nina New Starter",
            role=UserRole.employee,
        )
        db.add(pending)
        raw_token = issue_invite(pending, owner)

        zone = Location(
            business=business,
            name="Harbour St Car Wash",
            address="Darling Harbour, Sydney NSW",
            latitude=SHOP_LAT,
            longitude=SHOP_LNG,
            radius_m=SHOP_RADIUS_M,
        )
        db.add(zone)
        db.flush()

        _edited(db, _history(db, business, zone, staff), owner)
        db.commit()

        print(f"Seeded '{business.name}'.")
        print(f"  owner    {OWNER_EMAIL} / {DEMO_PASSWORD}")
        print(f"  manager  {MANAGER_EMAIL} / {DEMO_PASSWORD}")
        print(f"  employee {EMPLOYEE_EMAIL} / {DEMO_PASSWORD}")
        print(f"  pending invite: {invite_link(raw_token)}")
        print(f"  zone '{zone.name}' and a fortnight of shifts, one of them edited.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
