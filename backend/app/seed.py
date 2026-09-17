"""Development seed data: `python -m app.seed`."""

from datetime import UTC, datetime, timedelta

from app.config import settings
from app.database import SessionLocal
from app.models.business import Business, BusinessStatus
from app.models.user import User, UserRole, UserStatus
from app.services.auth import get_user_by_email
from app.services.invites import invite_link, issue_invite
from app.services.security import hash_password

DEMO_PASSWORD = "narademo123"
OWNER_EMAIL = "owner@carwash.demo"
MANAGER_EMAIL = "manager@carwash.demo"
EMPLOYEE_EMAIL = "employee@carwash.demo"
INVITED_EMAIL = "newstarter@carwash.demo"


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

        for email, name, role in (
            (MANAGER_EMAIL, "Marco Manager", UserRole.manager),
            (EMPLOYEE_EMAIL, "Eli Employee", UserRole.employee),
        ):
            db.add(
                User(
                    business=business,
                    email=email,
                    password_hash=hash_password(DEMO_PASSWORD),
                    full_name=name,
                    role=role,
                    status=UserStatus.active,
                    accepted_at=datetime.now(UTC),
                )
            )

        pending = User(
            business=business,
            email=INVITED_EMAIL,
            full_name="Nina New Starter",
            role=UserRole.employee,
        )
        db.add(pending)
        raw_token = issue_invite(pending, owner)
        db.commit()

        print(f"Seeded '{business.name}'.")
        print(f"  owner    {OWNER_EMAIL} / {DEMO_PASSWORD}")
        print(f"  manager  {MANAGER_EMAIL} / {DEMO_PASSWORD}")
        print(f"  employee {EMPLOYEE_EMAIL} / {DEMO_PASSWORD}")
        print(f"  pending invite: {invite_link(raw_token)}")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
