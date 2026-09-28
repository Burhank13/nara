"""Error alerting.

Without a DSN every function here is a no-op, which is what development and the test suite
want: a crash while you are writing code is not an alert, it is a traceback in your terminal.
"""

import logging

import sentry_sdk

from app.config import settings

logger = logging.getLogger("nara.observability")


def init() -> None:
    """Called once, before the app is built, so the SDK is armed for import-time failures too."""
    if not settings.sentry_dsn:
        logger.info("Sentry is off (no SENTRY_DSN set).")
        return

    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.environment,
        # Staff names, emails and the coordinates people clock in from are the whole database
        # here. An alert needs the stack trace, never the person it happened to.
        send_default_pii=False,
        traces_sample_rate=settings.sentry_traces_sample_rate,
    )
    logger.info("Sentry is on (environment: %s).", settings.environment)


def tag_request(request_id: str) -> None:
    """Tag everything this request reports with the id the caller was given.

    That tag is the point: someone quotes the request id from the error they saw and it goes
    straight to the event, instead of a search through everything that broke that minute.

    It is set at the start of the request rather than where a crash is caught, because Sentry
    reports an error the first time it sees it — and that is the `logger.exception` call, not
    the handler around it. Tagging afterwards is too late; the event has already gone.

    The scope is per-request (the ASGI integration isolates it), so this cannot leak onto
    another request being served at the same time.
    """
    if not settings.sentry_dsn:
        return

    sentry_sdk.set_tag("request_id", request_id)
