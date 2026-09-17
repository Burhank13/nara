from datetime import UTC, datetime, timedelta

from app.config import settings
from app.models.business import Business, BusinessStatus

# A failed payment is a grace period, not a lockout: past_due still writes.
WRITABLE_STATUSES = (BusinessStatus.trialing, BusinessStatus.active, BusinessStatus.past_due)


def effective_status(business: Business) -> BusinessStatus:
    """Deadlines apply the moment they pass, so neither state needs a nightly job to move it on."""
    now = datetime.now(UTC)

    if (
        business.status == BusinessStatus.trialing
        and business.trial_ends_at is not None
        and business.trial_ends_at <= now
    ):
        return BusinessStatus.read_only

    if (
        business.status == BusinessStatus.past_due
        and business.past_due_since is not None
        and business.past_due_since + timedelta(days=settings.past_due_grace_days) <= now
    ):
        return BusinessStatus.suspended

    return business.status


def is_writable(business: Business) -> bool:
    return effective_status(business) in WRITABLE_STATUSES


def grace_ends_at(business: Business) -> datetime | None:
    """When the current countdown runs out: the trial's end, or the end of a payment grace period."""
    if business.status == BusinessStatus.trialing:
        return business.trial_ends_at
    if business.status == BusinessStatus.past_due and business.past_due_since is not None:
        return business.past_due_since + timedelta(days=settings.past_due_grace_days)
    return None
