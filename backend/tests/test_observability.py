"""Sentry wiring.

The suite runs with no DSN, which is the configuration everyone develops against — so what
matters most here is that the alerting code is inert rather than broken when it is switched off.
"""

import logging

import pytest
import sentry_sdk
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app import observability
from app.config import settings


def test_the_suite_runs_with_alerting_switched_off() -> None:
    # If this ever fails, tests are reporting crashes to a real Sentry project.
    assert not settings.sentry_dsn


def test_tagging_is_harmless_when_there_is_no_dsn() -> None:
    # Called on every single request, so it has to be safe with nothing configured.
    observability.tag_request("abc123")


def test_init_is_a_no_op_without_a_dsn() -> None:
    observability.init()
    assert sentry_sdk.get_client().dsn is None


def test_a_crash_is_reported_once_and_tagged_with_the_request_id(monkeypatch, caplog) -> None:
    """The id in the error response has to be findable in Sentry, or it is just decoration.

    Two things this pins down, both learned the hard way: Sentry reports an exception the first
    time it sees it — which is the `logger.exception` call, not the handler around it — so the
    tag must already be on the scope by then. And because of that first-sighting rule, adding a
    `capture_exception` in the handler as well is silently deduped, not a second alert.
    """
    from app import middleware

    monkeypatch.setattr(settings, "sentry_dsn", "https://public@o0.ingest.sentry.io/1")
    observability.init()

    envelopes: list[object] = []
    monkeypatch.setattr(
        sentry_sdk.get_client().transport, "capture_envelope", lambda envelope: envelopes.append(envelope)
    )

    app = FastAPI()
    middleware.install(app)

    @app.get("/boom")
    def boom() -> None:
        raise RuntimeError("kaboom")

    with caplog.at_level(logging.ERROR), TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/boom")
    sentry_sdk.flush()

    assert response.status_code == 500
    body = response.json()["detail"]
    assert body["code"] == "server_error"
    assert "kaboom" not in response.text  # never leak the exception to the caller

    events = [
        item.payload.json
        for envelope in envelopes
        for item in envelope.items  # type: ignore[attr-defined]
        if item.headers.get("type") == "event"
    ]
    assert len(events) == 1, "a single crash must not raise two alerts"
    assert events[0]["tags"]["request_id"] == body["request_id"]


@pytest.fixture(autouse=True)
def _reset_sentry() -> None:
    """Leave the SDK off again, whatever a test in here did to it."""
    yield
    sentry_sdk.init(dsn=None)
