import uuid
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.shift import Shift, ShiftStatus
from app.services.payroll import round_hours
from tests.helpers import NEAR_SHOP, auth, create_zone, join, signup


def payroll_shop(client: TestClient) -> dict[str, str]:
    owner = signup(client)
    create_zone(client, owner["access_token"])
    employee = join(
        client,
        owner["access_token"],
        email="eli@sparklewash.com",
        role="employee",
        full_name="Eli Employee",
    )
    return {"owner": owner["access_token"], "employee": employee["access_token"]}


def logged_shift(client: TestClient, db: Session, token: str, *, start: datetime, end: datetime) -> None:
    """Clock in and out, then move the stored times to the hours we actually want to test."""
    client.post("/api/shifts/start", json=NEAR_SHOP, headers=auth(token))
    ended = client.post("/api/shifts/end", json=NEAR_SHOP, headers=auth(token))
    # Addressed by id: rows created in one transaction share a created_at, so "the latest" is ambiguous.
    shift = db.get(Shift, uuid.UUID(ended.json()["id"]))
    assert shift is not None
    shift.started_at = start
    shift.ended_at = end
    db.commit()


@pytest.mark.parametrize(
    ("hours", "increment", "expected"),
    [
        (7.13, 15, 7.25),
        (7.12, 15, 7.0),
        (8.0, 15, 8.0),
        # Half-up: banker's rounding would send this down to 7.0 and quietly short the wage.
        (7.125, 15, 7.25),
        (7.13, 0, 7.13),
        (3.99, 60, 4.0),
    ],
)
def test_hours_round_the_way_payroll_expects(hours: float, increment: int, expected: float) -> None:
    assert round_hours(hours, increment) == expected


def test_a_day_is_one_line_however_many_shifts_it_took(client: TestClient, db: Session) -> None:
    tokens = payroll_shop(client)
    morning = datetime.now(UTC) - timedelta(hours=9)
    logged_shift(client, db, tokens["employee"], start=morning, end=morning + timedelta(hours=3))
    logged_shift(
        client,
        db,
        tokens["employee"],
        start=morning + timedelta(hours=4),
        end=morning + timedelta(hours=8),
    )

    body = client.get("/api/payroll?period=week", headers=auth(tokens["owner"])).json()

    assert len(body["lines"]) == 1
    line = body["lines"][0]
    assert line["shift_count"] == 2
    assert line["hours"] == 7.0
    assert body["total_hours"] == 7.0


def test_an_unfinished_shift_holds_the_run_back(client: TestClient) -> None:
    tokens = payroll_shop(client)
    client.post("/api/shifts/start", json=NEAR_SHOP, headers=auth(tokens["employee"]))

    body = client.get("/api/payroll?period=week", headers=auth(tokens["owner"])).json()

    assert body["ready"] is False
    assert body["open_shifts"][0]["full_name"] == "Eli Employee"
    # An unfinished shift has no duration, so it must not be exported as if it did.
    assert body["lines"] == []


def test_people_without_a_payroll_code_are_named(client: TestClient, db: Session) -> None:
    tokens = payroll_shop(client)
    start = datetime.now(UTC) - timedelta(hours=5)
    logged_shift(client, db, tokens["employee"], start=start, end=start + timedelta(hours=4))

    body = client.get("/api/payroll?period=week", headers=auth(tokens["owner"])).json()

    assert body["missing_codes"] == ["Eli Employee"]


def test_the_owner_sets_a_payroll_code_and_it_reaches_the_export(client: TestClient, db: Session) -> None:
    tokens = payroll_shop(client)
    start = datetime.now(UTC) - timedelta(hours=5)
    logged_shift(client, db, tokens["employee"], start=start, end=start + timedelta(hours=4))
    team = client.get("/api/team", headers=auth(tokens["owner"])).json()
    eli = next(member for member in team["members"] if member["full_name"] == "Eli Employee")

    saved = client.patch(
        f"/api/team/members/{eli['id']}",
        json={"payroll_code": "EMP-001"},
        headers=auth(tokens["owner"]),
    )
    export = client.get("/api/payroll/export.csv?period=week", headers=auth(tokens["owner"]))

    assert saved.status_code == 200
    assert saved.json()["payroll_code"] == "EMP-001"
    lines = export.text.strip().splitlines()
    assert lines[0] == "Payroll code,Employee,Date,Hours"
    assert lines[1].startswith("EMP-001,Eli Employee,")
    assert lines[1].endswith(",4.00")


def test_two_people_cannot_share_a_payroll_code(client: TestClient) -> None:
    owner = signup(client)
    create_zone(client, owner["access_token"])
    join(client, owner["access_token"], email="eli@sparklewash.com", role="employee", full_name="Eli")
    join(client, owner["access_token"], email="mia@sparklewash.com", role="employee", full_name="Mia")
    team = client.get("/api/team", headers=auth(owner["access_token"])).json()
    first, second = (member for member in team["members"] if member["full_name"] in {"Eli", "Mia"})

    client.patch(
        f"/api/team/members/{first['id']}",
        json={"payroll_code": "SHARED"},
        headers=auth(owner["access_token"]),
    )
    clash = client.patch(
        f"/api/team/members/{second['id']}",
        json={"payroll_code": "SHARED"},
        headers=auth(owner["access_token"]),
    )

    assert clash.status_code == 409
    assert clash.json()["detail"]["code"] == "payroll_code_taken"


def test_payroll_is_owner_only(client: TestClient) -> None:
    tokens = payroll_shop(client)

    assert client.get("/api/payroll", headers=auth(tokens["employee"])).status_code == 403
    assert client.get("/api/payroll/export.csv", headers=auth(tokens["employee"])).status_code == 403


def test_a_shift_over_midnight_is_paid_against_the_day_it_started(client: TestClient, db: Session) -> None:
    tokens = payroll_shop(client)
    # 22:00 to 02:00 in Sydney, which is one 4-hour line on the starting day.
    start = datetime.now(UTC) - timedelta(hours=30)
    logged_shift(client, db, tokens["employee"], start=start, end=start + timedelta(hours=4))

    body = client.get("/api/payroll?period=month", headers=auth(tokens["owner"])).json()

    assert len(body["lines"]) == 1
    assert body["lines"][0]["hours"] == 4.0


def test_a_closed_shift_still_appears_after_an_owner_edit(client: TestClient, db: Session) -> None:
    tokens = payroll_shop(client)
    client.post("/api/shifts/start", json=NEAR_SHOP, headers=auth(tokens["employee"]))
    shift = db.execute(select(Shift)).scalars().one()
    assert shift.status == ShiftStatus.open

    body = client.get("/api/payroll?period=week", headers=auth(tokens["owner"])).json()
    assert body["ready"] is False
