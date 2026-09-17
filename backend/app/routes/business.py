import math
from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import require_owner, require_writable_business
from app.models.business import Business
from app.models.location import Location
from app.models.user import User, UserRole, UserStatus
from app.schemas.auth import BusinessResponse
from app.schemas.business import OnboardingResponse, OnboardingStep, UpdateBusinessRequest
from app.services.billing import grace_ends_at
from app.services.seats import get_seat_usage

router = APIRouter(prefix="/business", tags=["business"])


@router.patch("", response_model=BusinessResponse)
def update_business(
    payload: UpdateBusinessRequest,
    current_user: User = Depends(require_owner),
    business: Business = Depends(require_writable_business),
    db: Session = Depends(get_db),
) -> BusinessResponse:
    """Business details are the owner's to change; a manager has no settings access at all."""
    if payload.name is not None:
        business.name = payload.name.strip()
    if payload.abn is not None:
        business.abn = payload.abn
    if payload.timezone is not None:
        business.timezone = payload.timezone

    db.flush()
    db.refresh(business)
    return BusinessResponse.of(business)


@router.get("/onboarding", response_model=OnboardingResponse)
def onboarding(
    current_user: User = Depends(require_owner), db: Session = Depends(get_db)
) -> OnboardingResponse:
    """Setup progress is read back from the data itself, so it can never drift from reality."""
    business = current_user.business
    has_zone = db.execute(
        select(func.count())
        .select_from(Location)
        .where(Location.business_id == business.id, Location.is_active.is_(True))
    ).scalar_one()
    has_staff = db.execute(
        select(func.count())
        .select_from(User)
        .where(
            User.business_id == business.id,
            User.role != UserRole.owner,
            User.status != UserStatus.archived,
        )
    ).scalar_one()

    steps = [
        OnboardingStep(
            key="details",
            title="Business details",
            description="Your ABN and time zone, so hours land on the right day.",
            done=business.abn is not None,
        ),
        OnboardingStep(
            key="zones",
            title="Shop zones",
            description="Where staff can clock in. You can add more sites later.",
            done=has_zone > 0,
        ),
        OnboardingStep(
            key="staff",
            title="Add your team",
            description="Invite by email, or share a join link.",
            done=has_staff > 0,
        ),
        OnboardingStep(
            key="billing",
            title="Pick seats and pay",
            description="Or keep going on the trial and decide later.",
            done=business.stripe_subscription_id is not None,
            optional=True,
        ),
    ]
    required = [step for step in steps if not step.optional]
    usage = get_seat_usage(db, business)
    ends_at = grace_ends_at(business)

    return OnboardingResponse(
        steps=steps,
        complete=all(step.done for step in required),
        next_step=next((step.key for step in steps if not step.done), None),
        days_left=_days_left(ends_at),
        trial_ends_at=business.trial_ends_at,
        seats_used=usage.used,
        seat_limit=usage.limit,
    )


def _days_left(deadline: datetime | None) -> int | None:
    if deadline is None:
        return None
    return max(0, math.ceil((deadline - datetime.now(UTC)).total_seconds() / 86400))
