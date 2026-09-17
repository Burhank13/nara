from fastapi.testclient import TestClient

from tests.helpers import auth, invite, join, signup


def owner_with_team(client: TestClient) -> dict[str, dict]:
    owner = signup(client)
    manager = join(
        client,
        owner["access_token"],
        email="marco@sparklewash.com",
        role="manager",
        full_name="Marco Manager",
    )
    employee = join(
        client, owner["access_token"], email="eli@sparklewash.com", role="employee", full_name="Eli Employee"
    )
    return {"owner": owner, "manager": manager, "employee": employee}


def test_the_owner_sees_every_member_and_the_seat_count(client: TestClient) -> None:
    team = owner_with_team(client)

    response = client.get("/team", headers=auth(team["owner"]["access_token"]))

    assert response.status_code == 200
    body = response.json()
    assert {member["email"] for member in body["members"]} == {
        "olivia@sparklewash.com",
        "marco@sparklewash.com",
        "eli@sparklewash.com",
    }
    assert body["seats"] == {"used": 2, "limit": 10, "available": 8}


def test_a_manager_can_read_the_team(client: TestClient) -> None:
    team = owner_with_team(client)

    response = client.get("/team", headers=auth(team["manager"]["access_token"]))

    assert response.status_code == 200
    assert len(response.json()["members"]) == 3


def test_a_manager_cannot_invite_or_archive(client: TestClient) -> None:
    team = owner_with_team(client)
    manager_token = team["manager"]["access_token"]

    invited = client.post(
        "/team/invites",
        json={"email": "new@sparklewash.com", "full_name": "New Starter", "role": "employee"},
        headers=auth(manager_token),
    )
    archived = client.post(
        f"/team/members/{team['employee']['user']['id']}/archive", headers=auth(manager_token)
    )

    assert invited.status_code == 403
    assert invited.json()["detail"]["code"] == "forbidden"
    assert archived.status_code == 403


def test_a_manager_cannot_read_the_seat_meter(client: TestClient) -> None:
    team = owner_with_team(client)

    response = client.get("/team/seats", headers=auth(team["manager"]["access_token"]))

    assert response.status_code == 403


def test_an_employee_cannot_read_the_team(client: TestClient) -> None:
    team = owner_with_team(client)

    response = client.get("/team", headers=auth(team["employee"]["access_token"]))

    assert response.status_code == 403


def test_one_business_never_sees_another(client: TestClient) -> None:
    first = signup(client)
    first_employee = join(
        client, first["access_token"], email="eli@sparklewash.com", role="employee", full_name="Eli Employee"
    )
    second = signup(client, email="sam@shinewash.com", business_name="Shine Wash", full_name="Sam Owner")

    listed = client.get("/team", headers=auth(second["access_token"]))
    assert [member["email"] for member in listed.json()["members"]] == ["sam@shinewash.com"]
    assert listed.json()["seats"]["used"] == 0

    poached = client.post(
        f"/team/members/{first_employee['user']['id']}/archive", headers=auth(second["access_token"])
    )
    assert poached.status_code == 404
    assert poached.json()["detail"]["code"] == "member_not_found"


def test_an_invite_email_is_taken_even_in_another_business(client: TestClient) -> None:
    first = signup(client)
    invite(client, first["access_token"])
    second = signup(client, email="sam@shinewash.com", business_name="Shine Wash", full_name="Sam Owner")

    response = client.post(
        "/team/invites",
        json={"email": "eli@sparklewash.com", "full_name": "Eli Employee", "role": "employee"},
        headers=auth(second["access_token"]),
    )

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "email_taken"


def test_an_owner_cannot_be_invited_as_a_role_they_choose(client: TestClient) -> None:
    owner = signup(client)

    response = client.post(
        "/team/invites",
        json={"email": "second@sparklewash.com", "full_name": "Second Owner", "role": "owner"},
        headers=auth(owner["access_token"]),
    )

    assert response.status_code == 422
