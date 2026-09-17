from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.business import Business
from app.models.user import User
from tests.helpers import PASSWORD, accept, auth, invite, invite_token, join, signup


def member(db: Session, email: str) -> User:
    return db.execute(select(User).where(User.email == email)).scalar_one()


def business_of(db: Session, name: str = "Sparkle Car Wash") -> Business:
    return db.execute(select(Business).where(Business.name == name)).scalar_one()


def seats(client: TestClient, token: str) -> dict[str, int]:
    response = client.get("/api/team/seats", headers=auth(token))
    assert response.status_code == 200, response.text
    return response.json()


def test_invite_creates_a_pending_member_and_takes_a_seat(client: TestClient) -> None:
    owner = signup(client)

    body = invite(client, owner["access_token"])

    assert body["member"]["status"] == "invited"
    assert body["member"]["role"] == "employee"
    assert body["invite_url"].startswith("http")
    assert body["seats"] == {"used": 1, "limit": 10, "available": 9}


def test_the_owner_does_not_use_a_seat(client: TestClient) -> None:
    owner = signup(client)

    assert seats(client, owner["access_token"]) == {"used": 0, "limit": 10, "available": 10}


def test_an_invited_person_can_preview_and_accept_their_invite(client: TestClient) -> None:
    owner = signup(client)
    raw_token = invite_token(invite(client, owner["access_token"]))

    preview = client.get(f"/api/invites/{raw_token}")
    assert preview.status_code == 200
    assert preview.json()["business_name"] == "Sparkle Car Wash"
    assert preview.json()["email"] == "eli@sparklewash.com"

    accepted = accept(client, raw_token)
    assert accepted["user"]["status"] == "active"
    assert accepted["access_token"]

    login = client.post("/api/auth/login", json={"email": "eli@sparklewash.com", "password": PASSWORD})
    assert login.status_code == 200


def test_an_invite_token_only_works_once(client: TestClient) -> None:
    owner = signup(client)
    raw_token = invite_token(invite(client, owner["access_token"]))
    accept(client, raw_token)

    assert client.get(f"/api/invites/{raw_token}").status_code == 404
    response = client.post(
        f"/api/invites/{raw_token}/accept", json={"full_name": "Eli Employee", "password": PASSWORD}
    )
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "invalid_invite"


def test_an_expired_invite_is_refused(client: TestClient, db: Session) -> None:
    owner = signup(client)
    raw_token = invite_token(invite(client, owner["access_token"]))

    member(db, "eli@sparklewash.com").invite_expires_at = datetime.now(UTC) - timedelta(minutes=1)
    db.commit()

    assert client.get(f"/api/invites/{raw_token}").status_code == 404
    assert seats(client, owner["access_token"])["used"] == 0


def test_the_seat_limit_blocks_a_further_invite(client: TestClient, db: Session) -> None:
    owner = signup(client)
    business_of(db).seat_limit = 1
    db.commit()

    invite(client, owner["access_token"])
    response = client.post(
        "/api/team/invites",
        json={"email": "second@sparklewash.com", "full_name": "Second Starter", "role": "employee"},
        headers=auth(owner["access_token"]),
    )

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "seat_limit_reached"


def test_a_seat_limit_override_wins_over_the_stripe_quantity(client: TestClient, db: Session) -> None:
    owner = signup(client)
    business = business_of(db)
    business.seat_limit = 1
    business.seat_limit_override = 3
    db.commit()

    assert seats(client, owner["access_token"])["limit"] == 3


def test_resending_a_live_invite_does_not_need_a_spare_seat(client: TestClient, db: Session) -> None:
    owner = signup(client)
    business_of(db).seat_limit = 1
    db.commit()
    invited = invite(client, owner["access_token"])

    response = client.post(
        f"/api/team/members/{invited['member']['id']}/resend", headers=auth(owner["access_token"])
    )

    assert response.status_code == 200
    assert invite_token(response.json()) != invite_token(invited)
    assert client.get(f"/api/invites/{invite_token(invited)}").status_code == 404


def test_resending_an_expired_invite_needs_a_seat(client: TestClient, db: Session) -> None:
    owner = signup(client)
    invited = invite(client, owner["access_token"])
    invite(client, owner["access_token"], email="second@sparklewash.com", full_name="Second Starter")

    # The first invite lapsed, and the one remaining seat is held by the second.
    business_of(db).seat_limit = 1
    member(db, "eli@sparklewash.com").invite_expires_at = datetime.now(UTC) - timedelta(minutes=1)
    db.commit()

    response = client.post(
        f"/api/team/members/{invited['member']['id']}/resend", headers=auth(owner["access_token"])
    )

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "seat_limit_reached"


def test_resending_to_someone_who_already_joined_is_refused(client: TestClient) -> None:
    owner = signup(client)
    invited = invite(client, owner["access_token"])
    accept(client, invite_token(invited))

    response = client.post(
        f"/api/team/members/{invited['member']['id']}/resend", headers=auth(owner["access_token"])
    )

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "not_invited"


def test_revoking_an_invite_frees_the_seat(client: TestClient) -> None:
    owner = signup(client)
    invited = invite(client, owner["access_token"])

    response = client.delete(
        f"/api/team/members/{invited['member']['id']}", headers=auth(owner["access_token"])
    )

    assert response.status_code == 204
    assert seats(client, owner["access_token"])["used"] == 0


def test_an_invite_to_an_existing_email_is_refused(client: TestClient) -> None:
    owner = signup(client)
    invite(client, owner["access_token"])

    response = client.post(
        "/api/team/invites",
        json={"email": "eli@sparklewash.com", "full_name": "Eli Again", "role": "employee"},
        headers=auth(owner["access_token"]),
    )

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "email_taken"


def test_archiving_frees_a_seat_and_restoring_takes_it_back(client: TestClient) -> None:
    owner = signup(client)
    employee = join(
        client, owner["access_token"], email="eli@sparklewash.com", role="employee", full_name="Eli Employee"
    )
    employee_id = employee["user"]["id"]

    archived = client.post(f"/api/team/members/{employee_id}/archive", headers=auth(owner["access_token"]))
    assert archived.status_code == 200
    assert archived.json()["status"] == "archived"
    assert seats(client, owner["access_token"])["used"] == 0

    restored = client.post(f"/api/team/members/{employee_id}/restore", headers=auth(owner["access_token"]))
    assert restored.status_code == 200
    assert restored.json()["status"] == "active"
    assert seats(client, owner["access_token"])["used"] == 1


def test_an_archived_person_cannot_sign_in(client: TestClient) -> None:
    owner = signup(client)
    employee = join(
        client, owner["access_token"], email="eli@sparklewash.com", role="employee", full_name="Eli Employee"
    )
    client.post(f"/api/team/members/{employee['user']['id']}/archive", headers=auth(owner["access_token"]))

    response = client.post("/api/auth/login", json={"email": "eli@sparklewash.com", "password": PASSWORD})

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "account_inactive"


def test_the_owner_cannot_be_archived(client: TestClient) -> None:
    owner = signup(client)

    response = client.post(
        f"/api/team/members/{owner['user']['id']}/archive", headers=auth(owner["access_token"])
    )

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "cannot_archive_owner"


def test_someone_who_never_joined_is_re_invited_rather_than_restored(client: TestClient) -> None:
    owner = signup(client)
    invited = invite(client, owner["access_token"])
    client.post(f"/api/team/members/{invited['member']['id']}/archive", headers=auth(owner["access_token"]))

    restore = client.post(
        f"/api/team/members/{invited['member']['id']}/restore", headers=auth(owner["access_token"])
    )
    assert restore.status_code == 409
    assert restore.json()["detail"]["code"] == "never_joined"

    again = invite(client, owner["access_token"], full_name="Eli Employee")
    assert again["member"]["id"] == invited["member"]["id"]
    assert again["member"]["status"] == "invited"


def test_a_read_only_business_cannot_invite(client: TestClient, db: Session) -> None:
    owner = signup(client)
    business_of(db).trial_ends_at = datetime.now(UTC) - timedelta(days=1)
    db.commit()

    response = client.post(
        "/api/team/invites",
        json={"email": "eli@sparklewash.com", "full_name": "Eli Employee", "role": "employee"},
        headers=auth(owner["access_token"]),
    )

    assert response.status_code == 402
    assert response.json()["detail"]["code"] == "billing_inactive"
    assert client.get("/api/auth/me", headers=auth(owner["access_token"])).json()["business"]["status"] == (
        "read_only"
    )
