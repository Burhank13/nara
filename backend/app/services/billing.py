from datetime import UTC, datetime

from app.models.business import Business, BusinessStatus

WRITABLE_STATUSES = (BusinessStatus.trialing, BusinessStatus.active)


def effective_status(business: Business) -> BusinessStatus:
    """A trial past its end date behaves as read-only without waiting for a nightly job."""
    if (
        business.status == BusinessStatus.trialing
        and business.trial_ends_at is not None
        and business.trial_ends_at <= datetime.now(UTC)
    ):
        return BusinessStatus.read_only
    return business.status


def is_writable(business: Business) -> bool:
    return effective_status(business) in WRITABLE_STATUSES
