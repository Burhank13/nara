from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.shift import Shift
from tests.helpers import NEAR_SHOP, auth, create_zone, invite, join, signup


def busy_shop(client: TestClient) -> dict[str, str]:
    owner = signup(client)
    create_zone(client, owner["access_token"])
    employee = join(
        client,
        owner["access_token"],
        email="eli@sparklewash.com",
        role="employee",
        full_name="Eli Employee",
    )
    manager = join(
        client,
        owner["access_token"],
        email="marco@sparklewash.com",
        role="manager",
        full_name="Marco Manager",
    )
    return {
        "owner": owner["access_token"],
        "employee": employee["access_token"],
        "manager": manager["access_token"],
    }


def test_the_live_board_lists_who_is_on_shift(client: TestClient) -> None:
    tokens = busy_shop(client)
    client.post("/api/shifts/start", json=NEAR_SHOP, headers=auth(tokens["employee"]))

    response = client.get("/api/shifts/live", headers=auth(tokens["owner"]))

    assert response.status_code == 200
    body = response.json()
    assert body["staff_count"] == 2
    assert len(body["on_shift"]) == 1
    entry = body["on_shift"][0]
    assert entry["full_name"] == "Eli Employee"
    assert entry["location_name"] == "Harbour St Car Wash"
    assert entry["start_distance_m"] == 40
    assert entry["needs_attention"] is False


def test_a_manager_sees_the_live_board_but_an_employee_does_not(client: TestClient) -> None:
    tokens = busy_shop(client)

    assert client.get("/api/shifts/live", headers=auth(tokens["manager"])).status_code == 200
    assert client.get("/api/shifts/live", headers=auth(tokens["employee"])).status_code == 403


def test_a_shift_left_open_too_long_is_flagged(client: TestClient, db: Session) -> None:
    tokens = busy_shop(client)
    client.post("/api/shifts/start", json=NEAR_SHOP, headers=auth(tokens["employee"]))

    shift = db.execute(select(Shift)).scalar_one()
    shift.started_at = datetime.now(UTC) - timedelta(hours=13)
    db.commit()

    response = client.get("/api/shifts/live", headers=auth(tokens["owner"]))

    assert response.json()["on_shift"][0]["needs_attention"] is True


def test_the_overview_counts_staff_shifts_and_hours(client: TestClient) -> None:
    tokens = busy_shop(client)
    invite(client, tokens["owner"], email="pending@sparklewash.com", full_name="Pat Pending")
    client.post("/api/shifts/start", json=NEAR_SHOP, headers=auth(tokens["employee"]))
    client.post("/api/shifts/end", json=NEAR_SHOP, headers=auth(tokens["employee"]))
    client.post("/api/shifts/start", json=NEAR_SHOP, headers=auth(tokens["manager"]))

    response = client.get("/api/overview?period=week", headers=auth(tokens["owner"]))

    assert response.status_code == 200
    body = response.json()
    assert body["active_count"] == 2
    assert body["invited_count"] == 1
    assert body["staff_count"] == 3
    assert body["shift_count"] == 2
    assert len(body["on_shift"]) == 1
    assert body["needs_attention"] == []
    assert {row["full_name"] for row in body["hours_by_employee"]} == {
        "Eli Employee",
        "Marco Manager",
    }


def test_the_overview_is_owner_only(client: TestClient) -> None:
    tokens = busy_shop(client)

    assert client.get("/api/overview", headers=auth(tokens["manager"])).status_code == 403
    assert client.get("/api/overview", headers=auth(tokens["employee"])).status_code == 403


def test_the_overview_only_counts_this_business(client: TestClient) -> None:
    tokens = busy_shop(client)
    client.post("/api/shifts/start", json=NEAR_SHOP, headers=auth(tokens["employee"]))
    other = signup(client, email="sam@shinewash.com", business_name="Shine Wash", full_name="Sam Owner")

    response = client.get("/api/overview", headers=auth(other["access_token"]))

    body = response.json()
    assert body["staff_count"] == 0
    assert body["on_shift"] == []
    assert body["shift_count"] == 0
