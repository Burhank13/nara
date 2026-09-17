from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from tests.helpers import PASSWORD, auth, signup


def test_signup_opens_a_trialing_business_with_ten_seats(client: TestClient) -> None:
    body = signup(client)

    assert body["user"]["role"] == "owner"
    assert body["user"]["status"] == "active"
    assert body["business"]["status"] == "trialing"
    assert body["business"]["seat_limit"] == 10
    assert body["business"]["timezone"] == "Australia/Sydney"
    assert body["access_token"]

    trial_ends_at = datetime.fromisoformat(body["business"]["trial_ends_at"])
    assert timedelta(days=13) < trial_ends_at - datetime.now(UTC) <= timedelta(days=14)
    assert client.cookies.get("nara_refresh")


def test_signup_rejects_a_duplicate_email(client: TestClient) -> None:
    signup(client)
    response = client.post(
        "/auth/signup",
        json={
            "email": "olivia@sparklewash.com",
            "business_name": "Another Wash",
            "full_name": "Someone Else",
            "password": PASSWORD,
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "email_taken"


def test_signup_rejects_an_unknown_timezone(client: TestClient) -> None:
    response = client.post(
        "/auth/signup",
        json={
            "email": "olivia@sparklewash.com",
            "business_name": "Sparkle Car Wash",
            "full_name": "Olivia Owner",
            "password": PASSWORD,
            "timezone": "Mars/Olympus_Mons",
        },
    )

    assert response.status_code == 422


def test_signup_rejects_a_password_over_the_bcrypt_limit(client: TestClient) -> None:
    response = client.post(
        "/auth/signup",
        json={
            "email": "olivia@sparklewash.com",
            "business_name": "Sparkle Car Wash",
            "full_name": "Olivia Owner",
            "password": "a" * 73,
        },
    )

    assert response.status_code == 422


def test_login_returns_a_session(client: TestClient) -> None:
    signup(client)

    response = client.post("/auth/login", json={"email": "olivia@sparklewash.com", "password": PASSWORD})

    assert response.status_code == 200
    assert response.json()["user"]["email"] == "olivia@sparklewash.com"


def test_login_is_case_insensitive_on_email(client: TestClient) -> None:
    signup(client)

    response = client.post("/auth/login", json={"email": "Olivia@SparkleWash.com", "password": PASSWORD})

    assert response.status_code == 200


def test_login_rejects_a_wrong_password(client: TestClient) -> None:
    signup(client)

    response = client.post("/auth/login", json={"email": "olivia@sparklewash.com", "password": "wrong-one"})

    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "invalid_credentials"


def test_login_rejects_an_unknown_email(client: TestClient) -> None:
    response = client.post("/auth/login", json={"email": "nobody@sparklewash.com", "password": PASSWORD})

    assert response.status_code == 401


def test_me_returns_the_signed_in_user_and_business(client: TestClient) -> None:
    body = signup(client)

    response = client.get("/auth/me", headers=auth(body["access_token"]))

    assert response.status_code == 200
    assert response.json()["user"]["id"] == body["user"]["id"]
    assert response.json()["business"]["name"] == "Sparkle Car Wash"


def test_me_without_a_token_is_rejected(client: TestClient) -> None:
    response = client.get("/auth/me")

    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "not_authenticated"


def test_me_with_a_junk_token_is_rejected(client: TestClient) -> None:
    response = client.get("/auth/me", headers=auth("not-a-real-token"))

    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "invalid_token"


def test_refresh_issues_a_new_access_token_from_the_cookie(client: TestClient) -> None:
    signup(client)

    response = client.post("/auth/refresh")

    assert response.status_code == 200
    assert response.json()["access_token"]


def test_refresh_without_a_cookie_is_rejected(client: TestClient) -> None:
    signup(client)
    client.cookies.clear()

    response = client.post("/auth/refresh")

    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "not_authenticated"


def test_an_access_token_cannot_be_used_as_a_refresh_token(client: TestClient) -> None:
    body = signup(client)
    client.cookies.clear()
    client.cookies.set("nara_refresh", body["access_token"])

    response = client.post("/auth/refresh")

    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "invalid_token"


def test_logout_clears_the_refresh_cookie(client: TestClient) -> None:
    signup(client)

    assert client.post("/auth/logout").status_code == 204
    assert client.post("/auth/refresh").status_code == 401
