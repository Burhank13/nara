from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.business import Business, BusinessStatus
from tests.helpers import NEAR_SHOP, auth, create_zone, invite, join, signup

# Valid ABNs (they carry a checksum), plus one that is 11 digits but fails it.
GOOD_ABN = "51824753556"
BAD_CHECKSUM_ABN = "51824753557"


def set_status(db: Session, status: BusinessStatus, **fields: object) -> Business:
    business = db.execute(select(Business)).scalars().first()
    assert business is not None
    business.status = status
    for key, value in fields.items():
        setattr(business, key, value)
    db.commit()
    return business


def test_the_owner_can_fill_in_the_business_details(client: TestClient) -> None:
    owner = signup(client)

    response = client.patch(
        "/api/business",
        json={"abn": "51 824 753 556", "timezone": "Australia/Perth", "name": "Sparkle Wash Perth"},
        headers=auth(owner["access_token"]),
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["abn"] == GOOD_ABN
    assert body["timezone"] == "Australia/Perth"
    assert body["name"] == "Sparkle Wash Perth"


def test_a_mistyped_abn_is_refused(client: TestClient) -> None:
    owner = signup(client)

    for value in (BAD_CHECKSUM_ABN, "12345", "abcdefghijk"):
        response = client.patch("/api/business", json={"abn": value}, headers=auth(owner["access_token"]))
        assert response.status_code == 422, value


def test_only_the_owner_changes_business_details(client: TestClient) -> None:
    owner = signup(client)
    manager = join(
        client, owner["access_token"], email="marco@sparklewash.com", role="manager", full_name="Marco"
    )

    response = client.patch(
        "/api/business", json={"name": "Renamed by a manager"}, headers=auth(manager["access_token"])
    )

    assert response.status_code == 403


def test_onboarding_tracks_what_is_actually_set_up(client: TestClient) -> None:
    owner = signup(client)
    token = owner["access_token"]

    start = client.get("/api/business/onboarding", headers=auth(token)).json()
    assert start["complete"] is False
    assert start["next_step"] == "details"
    assert {step["key"]: step["done"] for step in start["steps"]} == {
        "details": False,
        "zones": False,
        "staff": False,
        "billing": False,
    }

    client.patch("/api/business", json={"abn": GOOD_ABN}, headers=auth(token))
    create_zone(client, token)
    invite(client, token)

    done = client.get("/api/business/onboarding", headers=auth(token)).json()
    assert done["complete"] is True
    # Billing is the only step left, and it is the optional one.
    assert done["next_step"] == "billing"
    assert next(step for step in done["steps"] if step["key"] == "billing")["optional"] is True
    assert done["seats_used"] == 1
    assert done["seat_limit"] == 10


def test_onboarding_counts_down_the_trial(client: TestClient) -> None:
    owner = signup(client)

    body = client.get("/api/business/onboarding", headers=auth(owner["access_token"])).json()

    assert body["days_left"] == 14


def test_a_past_due_business_keeps_working_through_the_grace_period(client: TestClient, db: Session) -> None:
    owner = signup(client)
    create_zone(client, owner["access_token"])
    employee = join(
        client, owner["access_token"], email="eli@sparklewash.com", role="employee", full_name="Eli"
    )
    set_status(db, BusinessStatus.past_due, past_due_since=datetime.now(UTC) - timedelta(days=2))

    started = client.post("/api/shifts/start", json=NEAR_SHOP, headers=auth(employee["access_token"]))
    session = client.get("/api/auth/me", headers=auth(owner["access_token"])).json()

    assert started.status_code == 201
    assert session["business"]["status"] == "past_due"
    assert session["business"]["grace_ends_at"] is not None


def test_an_unpaid_business_suspends_itself_once_the_grace_period_lapses(
    client: TestClient, db: Session
) -> None:
    owner = signup(client)
    create_zone(client, owner["access_token"])
    employee = join(
        client, owner["access_token"], email="eli@sparklewash.com", role="employee", full_name="Eli"
    )
    set_status(db, BusinessStatus.past_due, past_due_since=datetime.now(UTC) - timedelta(days=8))

    started = client.post("/api/shifts/start", json=NEAR_SHOP, headers=auth(employee["access_token"]))
    session = client.get("/api/auth/me", headers=auth(owner["access_token"])).json()

    assert started.status_code == 402
    assert session["business"]["status"] == "suspended"


def test_an_expired_trial_stops_new_shifts_but_still_lets_the_owner_export(
    client: TestClient, db: Session
) -> None:
    owner = signup(client)
    create_zone(client, owner["access_token"])
    employee = join(
        client, owner["access_token"], email="eli@sparklewash.com", role="employee", full_name="Eli"
    )
    client.post("/api/shifts/start", json=NEAR_SHOP, headers=auth(employee["access_token"]))
    set_status(db, BusinessStatus.trialing, trial_ends_at=datetime.now(UTC) - timedelta(minutes=1))

    ended = client.post("/api/shifts/end", json={}, headers=auth(employee["access_token"]))
    restarted = client.post("/api/shifts/start", json=NEAR_SHOP, headers=auth(employee["access_token"]))
    export = client.get("/api/timesheets/export.csv", headers=auth(owner["access_token"]))

    # Ending always works, so nobody is trapped on the clock by an expired trial.
    assert ended.status_code == 200
    assert restarted.status_code == 402
    assert export.status_code == 200
