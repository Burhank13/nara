from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient

from tests.helpers import NEAR_SHOP, auth, create_zone, join, signup

SYDNEY = ZoneInfo("Australia/Sydney")


def shop_local(hours_ago: float) -> str:
    """A wall-clock time in the shop's zone, which is what the edit endpoint takes."""
    moment = datetime.now(SYDNEY) - timedelta(hours=hours_ago)
    return moment.replace(microsecond=0, tzinfo=None).isoformat()


def worked_shop(client: TestClient) -> dict[str, str]:
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


def a_closed_shift(client: TestClient, token: str) -> str:
    client.post("/api/shifts/start", json=NEAR_SHOP, headers=auth(token))
    response = client.post("/api/shifts/end", json=NEAR_SHOP, headers=auth(token))
    return response.json()["id"]


def test_the_timesheet_lists_every_shift_with_who_worked_it(client: TestClient) -> None:
    tokens = worked_shop(client)
    a_closed_shift(client, tokens["employee"])
    a_closed_shift(client, tokens["manager"])

    response = client.get("/api/timesheets?period=week", headers=auth(tokens["owner"]))

    assert response.status_code == 200
    body = response.json()
    assert body["shift_count"] == 2
    assert body["open_count"] == 0
    assert {row["full_name"] for row in body["shifts"]} == {"Eli Employee", "Marco Manager"}
    assert {row["full_name"] for row in body["staff"]} == {
        "Olivia Owner",
        "Eli Employee",
        "Marco Manager",
    }


def test_the_timesheet_can_be_filtered_to_one_person(client: TestClient) -> None:
    tokens = worked_shop(client)
    a_closed_shift(client, tokens["employee"])
    a_closed_shift(client, tokens["manager"])

    everyone = client.get("/api/timesheets?period=week", headers=auth(tokens["owner"])).json()
    eli = next(row for row in everyone["shifts"] if row["full_name"] == "Eli Employee")

    response = client.get(
        f"/api/timesheets?period=week&user_id={eli['user_id']}", headers=auth(tokens["owner"])
    )

    body = response.json()
    assert body["shift_count"] == 1
    assert body["shifts"][0]["full_name"] == "Eli Employee"


def test_the_timesheet_is_owner_only(client: TestClient) -> None:
    tokens = worked_shop(client)

    assert client.get("/api/timesheets", headers=auth(tokens["manager"])).status_code == 403
    assert client.get("/api/timesheets", headers=auth(tokens["employee"])).status_code == 403


def test_an_edit_changes_the_hours_and_records_the_reason(client: TestClient) -> None:
    tokens = worked_shop(client)
    shift_id = a_closed_shift(client, tokens["employee"])

    response = client.patch(
        f"/api/shifts/{shift_id}",
        json={
            "started_at": shop_local(9),
            "ended_at": shop_local(1),
            "reason": "Forgot to clock in at the start of the day",
        },
        headers=auth(tokens["owner"]),
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["hours"] == 8.0
    assert len(body["edits"]) == 1
    entry = body["edits"][0]
    assert entry["edited_by"] == "Olivia Owner"
    assert entry["reason"] == "Forgot to clock in at the start of the day"
    assert entry["previous_started_at"] != entry["new_started_at"]


def test_an_edit_needs_a_reason(client: TestClient) -> None:
    tokens = worked_shop(client)
    shift_id = a_closed_shift(client, tokens["employee"])

    blank = client.patch(
        f"/api/shifts/{shift_id}",
        json={"started_at": shop_local(3), "reason": "   "},
        headers=auth(tokens["owner"]),
    )
    missing = client.patch(
        f"/api/shifts/{shift_id}",
        json={"started_at": shop_local(3)},
        headers=auth(tokens["owner"]),
    )

    assert blank.status_code == 422
    assert missing.status_code == 422


def test_giving_an_open_shift_an_end_time_closes_it(client: TestClient) -> None:
    tokens = worked_shop(client)
    started = client.post("/api/shifts/start", json=NEAR_SHOP, headers=auth(tokens["employee"]))
    shift_id = started.json()["id"]

    response = client.patch(
        f"/api/shifts/{shift_id}",
        json={
            "started_at": shop_local(8),
            "ended_at": shop_local(2),
            "reason": "Missed clock-out, went home at 4",
        },
        headers=auth(tokens["owner"]),
    )

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "closed"
    assert response.json()["hours"] == 6.0
    # The open-shift slot is free again, so they can start tomorrow.
    assert (
        client.post("/api/shifts/start", json=NEAR_SHOP, headers=auth(tokens["employee"])).status_code == 201
    )


def test_impossible_times_are_refused(client: TestClient) -> None:
    tokens = worked_shop(client)
    shift_id = a_closed_shift(client, tokens["employee"])
    reason = "Correcting the logged times"

    backwards = client.patch(
        f"/api/shifts/{shift_id}",
        json={"started_at": shop_local(2), "ended_at": shop_local(5), "reason": reason},
        headers=auth(tokens["owner"]),
    )
    future = client.patch(
        f"/api/shifts/{shift_id}",
        json={"ended_at": shop_local(-3), "reason": reason},
        headers=auth(tokens["owner"]),
    )
    unchanged = client.patch(
        f"/api/shifts/{shift_id}", json={"reason": reason}, headers=auth(tokens["owner"])
    )

    assert backwards.status_code == 409
    assert backwards.json()["detail"]["code"] == "end_before_start"
    assert future.status_code == 409
    assert future.json()["detail"]["code"] == "future_time"
    assert unchanged.status_code == 400
    assert unchanged.json()["detail"]["code"] == "nothing_to_change"


def test_only_the_owner_can_edit_a_shift(client: TestClient) -> None:
    tokens = worked_shop(client)
    shift_id = a_closed_shift(client, tokens["employee"])
    payload = {"started_at": shop_local(4), "reason": "Trying to change my own hours"}

    assert (
        client.patch(f"/api/shifts/{shift_id}", json=payload, headers=auth(tokens["manager"])).status_code
        == 403
    )
    assert (
        client.patch(f"/api/shifts/{shift_id}", json=payload, headers=auth(tokens["employee"])).status_code
        == 403
    )


def test_an_owner_cannot_edit_another_businesss_shift(client: TestClient) -> None:
    tokens = worked_shop(client)
    shift_id = a_closed_shift(client, tokens["employee"])
    other = signup(client, email="sam@shinewash.com", business_name="Shine Wash", full_name="Sam Owner")

    response = client.patch(
        f"/api/shifts/{shift_id}",
        json={"started_at": shop_local(4), "reason": "Not my business to edit"},
        headers=auth(other["access_token"]),
    )

    assert response.status_code == 404


def test_the_employee_sees_the_edit_on_their_own_hours(client: TestClient) -> None:
    tokens = worked_shop(client)
    shift_id = a_closed_shift(client, tokens["employee"])
    client.patch(
        f"/api/shifts/{shift_id}",
        json={"started_at": shop_local(6), "reason": "You started before the app was open"},
        headers=auth(tokens["owner"]),
    )

    response = client.get("/api/shifts/mine?period=week", headers=auth(tokens["employee"]))

    shift = response.json()["shifts"][0]
    assert shift["edits"][0]["reason"] == "You started before the app was open"
    assert shift["edits"][0]["edited_by"] == "Olivia Owner"


def test_the_export_returns_a_csv_of_the_period(client: TestClient) -> None:
    tokens = worked_shop(client)
    a_closed_shift(client, tokens["employee"])

    response = client.get("/api/timesheets/export.csv?period=week", headers=auth(tokens["owner"]))

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "attachment; filename=" in response.headers["content-disposition"]
    lines = response.text.strip().splitlines()
    assert lines[0].startswith("Employee,Date,Start,End,Hours,Status,Location")
    assert "Eli Employee" in lines[1]
    assert "Harbour St Car Wash" in lines[1]


def test_the_export_is_owner_only(client: TestClient) -> None:
    tokens = worked_shop(client)

    assert client.get("/api/timesheets/export.csv", headers=auth(tokens["manager"])).status_code == 403
    assert client.get("/api/timesheets/export.csv", headers=auth(tokens["employee"])).status_code == 403


def test_a_name_that_looks_like_a_formula_cannot_run_in_a_spreadsheet(client: TestClient) -> None:
    owner = signup(client)
    create_zone(client, owner["access_token"])
    sneaky = join(
        client,
        owner["access_token"],
        email="sneaky@sparklewash.com",
        role="employee",
        full_name="=1+1",
    )
    a_closed_shift(client, sneaky["access_token"])

    response = client.get("/api/timesheets/export.csv?period=week", headers=auth(owner["access_token"]))

    assert "'=1+1" in response.text
