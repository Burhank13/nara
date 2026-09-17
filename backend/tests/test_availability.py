from fastapi.testclient import TestClient

from tests.helpers import auth, join, signup

WEEK = {
    "days": [
        {"weekday": 0, "start_time": "07:00", "end_time": "15:00"},
        {"weekday": 1, "start_time": "07:00", "end_time": "15:00"},
        {"weekday": 4, "start_time": "12:00", "end_time": "18:00"},
    ]
}


def staffed_shop(client: TestClient) -> dict[str, str]:
    owner = signup(client)
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


def test_someone_sets_and_reads_back_their_week(client: TestClient) -> None:
    tokens = staffed_shop(client)

    saved = client.put("/api/availability/mine", json=WEEK, headers=auth(tokens["employee"]))
    read = client.get("/api/availability/mine", headers=auth(tokens["employee"]))

    assert saved.status_code == 200, saved.text
    assert len(saved.json()["days"]) == 3
    assert read.json()["days"][0] == {"weekday": 0, "start_time": "07:00:00", "end_time": "15:00:00"}


def test_saving_the_week_replaces_what_was_there(client: TestClient) -> None:
    tokens = staffed_shop(client)
    client.put("/api/availability/mine", json=WEEK, headers=auth(tokens["employee"]))

    response = client.put(
        "/api/availability/mine",
        json={"days": [{"weekday": 2, "start_time": "09:00", "end_time": "17:00"}]},
        headers=auth(tokens["employee"]),
    )

    assert [day["weekday"] for day in response.json()["days"]] == [2]


def test_an_empty_week_clears_availability(client: TestClient) -> None:
    tokens = staffed_shop(client)
    client.put("/api/availability/mine", json=WEEK, headers=auth(tokens["employee"]))

    response = client.put("/api/availability/mine", json={"days": []}, headers=auth(tokens["employee"]))

    assert response.json()["days"] == []


def test_a_window_that_ends_before_it_starts_is_refused(client: TestClient) -> None:
    tokens = staffed_shop(client)

    response = client.put(
        "/api/availability/mine",
        json={"days": [{"weekday": 0, "start_time": "17:00", "end_time": "09:00"}]},
        headers=auth(tokens["employee"]),
    )

    assert response.status_code == 422


def test_the_same_weekday_cannot_be_listed_twice(client: TestClient) -> None:
    tokens = staffed_shop(client)

    response = client.put(
        "/api/availability/mine",
        json={
            "days": [
                {"weekday": 3, "start_time": "09:00", "end_time": "12:00"},
                {"weekday": 3, "start_time": "13:00", "end_time": "17:00"},
            ]
        },
        headers=auth(tokens["employee"]),
    )

    assert response.status_code == 422


def test_the_owner_grid_shows_every_active_staff_member(client: TestClient) -> None:
    tokens = staffed_shop(client)
    client.put("/api/availability/mine", json=WEEK, headers=auth(tokens["employee"]))

    response = client.get("/api/availability/team", headers=auth(tokens["owner"]))

    assert response.status_code == 200
    members = response.json()["members"]
    # The owner is not in the grid; both staff are, even the one who set nothing.
    assert [member["full_name"] for member in members] == ["Eli Employee", "Marco Manager"]
    assert len(members[0]["days"]) == 3
    assert members[1]["days"] == []


def test_a_manager_can_read_the_grid_but_an_employee_cannot(client: TestClient) -> None:
    tokens = staffed_shop(client)

    assert client.get("/api/availability/team", headers=auth(tokens["manager"])).status_code == 200
    assert client.get("/api/availability/team", headers=auth(tokens["employee"])).status_code == 403


def test_one_business_never_sees_another_business_availability(client: TestClient) -> None:
    tokens = staffed_shop(client)
    client.put("/api/availability/mine", json=WEEK, headers=auth(tokens["employee"]))
    other = signup(client, email="sam@shinewash.com", business_name="Shine Wash", full_name="Sam Owner")

    response = client.get("/api/availability/team", headers=auth(other["access_token"]))

    assert response.json()["members"] == []
