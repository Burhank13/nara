from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User
from app.services.email import Email
from app.services.password_reset import hash_reset_token
from tests.helpers import PASSWORD, auth, invite, signup

NEW_PASSWORD = "a-brand-new-password"


def captured(monkeypatch) -> list[Email]:
    """Nothing leaves the process: the suite asserts on what would have been sent."""
    sent: list[Email] = []
    monkeypatch.setattr("app.routes.auth.send", lambda email: sent.append(email) or True)
    return sent


def token_for(db: Session, email: str) -> str:
    """Tests only ever see the hash, so the raw token is recovered from the emailed link."""
    user = db.execute(select(User).where(User.email == email)).scalar_one()
    assert user.reset_token_hash is not None
    return user.reset_token_hash


def link_token(sent: list[Email]) -> str:
    return sent[-1].html.split("/reset/")[1].split('"')[0]


def test_a_reset_link_is_emailed_and_sets_a_new_password(
    client: TestClient, db: Session, monkeypatch
) -> None:
    sent = captured(monkeypatch)
    signup(client, email="olivia@sparklewash.com")

    asked = client.post("/api/auth/forgot-password", json={"email": "olivia@sparklewash.com"})
    assert asked.status_code == 204
    assert len(sent) == 1
    assert sent[0].to == "olivia@sparklewash.com"

    raw_token = link_token(sent)
    reset = client.post("/api/auth/reset-password", json={"token": raw_token, "password": NEW_PASSWORD})
    assert reset.status_code == 204

    assert (
        client.post(
            "/api/auth/login", json={"email": "olivia@sparklewash.com", "password": NEW_PASSWORD}
        ).status_code
        == 200
    )
    assert (
        client.post(
            "/api/auth/login", json={"email": "olivia@sparklewash.com", "password": PASSWORD}
        ).status_code
        == 401
    )


def test_an_unknown_address_is_answered_the_same_way(client: TestClient, monkeypatch) -> None:
    sent = captured(monkeypatch)

    response = client.post("/api/auth/forgot-password", json={"email": "nobody@sparklewash.com"})

    # Same 204 as a real address: this endpoint must not reveal who has an account.
    assert response.status_code == 204
    assert sent == []


def test_a_link_works_only_once(client: TestClient, monkeypatch) -> None:
    sent = captured(monkeypatch)
    signup(client, email="olivia@sparklewash.com")
    client.post("/api/auth/forgot-password", json={"email": "olivia@sparklewash.com"})
    raw_token = link_token(sent)

    first = client.post("/api/auth/reset-password", json={"token": raw_token, "password": NEW_PASSWORD})
    second = client.post(
        "/api/auth/reset-password", json={"token": raw_token, "password": "another-password-1"}
    )

    assert first.status_code == 204
    assert second.status_code == 404
    assert second.json()["detail"]["code"] == "reset_invalid"


def test_an_expired_link_is_refused(client: TestClient, db: Session, monkeypatch) -> None:
    sent = captured(monkeypatch)
    signup(client, email="olivia@sparklewash.com")
    client.post("/api/auth/forgot-password", json={"email": "olivia@sparklewash.com"})
    raw_token = link_token(sent)

    user = db.execute(select(User).where(User.email == "olivia@sparklewash.com")).scalar_one()
    user.reset_expires_at = datetime.now(UTC) - timedelta(minutes=1)
    db.commit()

    preview = client.get(f"/api/auth/reset/{raw_token}")
    used = client.post("/api/auth/reset-password", json={"token": raw_token, "password": NEW_PASSWORD})

    assert preview.status_code == 404
    assert used.status_code == 404


def test_the_preview_names_the_account_before_a_password_is_typed(client: TestClient, monkeypatch) -> None:
    sent = captured(monkeypatch)
    signup(client, email="olivia@sparklewash.com")
    client.post("/api/auth/forgot-password", json={"email": "olivia@sparklewash.com"})

    response = client.get(f"/api/auth/reset/{link_token(sent)}")

    assert response.status_code == 200
    assert response.json() == {"email": "olivia@sparklewash.com", "full_name": "Olivia Owner"}


def test_resetting_signs_out_everywhere(client: TestClient, monkeypatch) -> None:
    sent = captured(monkeypatch)
    owner = signup(client, email="olivia@sparklewash.com")
    stolen = owner["access_token"]
    assert client.get("/api/auth/me", headers=auth(stolen)).status_code == 200

    client.post("/api/auth/forgot-password", json={"email": "olivia@sparklewash.com"})
    client.post("/api/auth/reset-password", json={"token": link_token(sent), "password": NEW_PASSWORD})

    # The point of resetting is often that someone else is signed in. They must be kicked out.
    response = client.get("/api/auth/me", headers=auth(stolen))
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "session_revoked"


def test_a_reset_clears_a_lockout(client: TestClient, monkeypatch) -> None:
    from app.config import settings

    sent = captured(monkeypatch)
    signup(client, email="olivia@sparklewash.com")
    wrong = {"email": "olivia@sparklewash.com", "password": "not-the-password"}
    for _ in range(settings.max_failed_logins):
        client.post("/api/auth/login", json=wrong)
    assert client.post("/api/auth/login", json=wrong).status_code == 429

    client.post("/api/auth/forgot-password", json={"email": "olivia@sparklewash.com"})
    client.post("/api/auth/reset-password", json={"token": link_token(sent), "password": NEW_PASSWORD})

    # Locked out and forgotten the password is exactly when someone resets it.
    assert (
        client.post(
            "/api/auth/login", json={"email": "olivia@sparklewash.com", "password": NEW_PASSWORD}
        ).status_code
        == 200
    )


def test_an_invited_user_who_never_joined_gets_no_reset(client: TestClient, monkeypatch) -> None:
    sent = captured(monkeypatch)
    owner = signup(client)
    invite(client, owner["access_token"], email="newstarter@sparklewash.com", full_name="Nina New")
    sent.clear()

    response = client.post("/api/auth/forgot-password", json={"email": "newstarter@sparklewash.com"})

    # They have no password to reset; their invite is the way in.
    assert response.status_code == 204
    assert sent == []


def test_a_short_password_is_refused(client: TestClient, monkeypatch) -> None:
    sent = captured(monkeypatch)
    signup(client, email="olivia@sparklewash.com")
    client.post("/api/auth/forgot-password", json={"email": "olivia@sparklewash.com"})

    response = client.post("/api/auth/reset-password", json={"token": link_token(sent), "password": "short"})

    assert response.status_code == 422


def test_the_stored_token_is_only_a_hash(client: TestClient, db: Session, monkeypatch) -> None:
    sent = captured(monkeypatch)
    signup(client, email="olivia@sparklewash.com")
    client.post("/api/auth/forgot-password", json={"email": "olivia@sparklewash.com"})

    raw_token = link_token(sent)
    stored = token_for(db, "olivia@sparklewash.com")

    assert stored != raw_token
    assert stored == hash_reset_token(raw_token)
