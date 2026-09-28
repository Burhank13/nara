from fastapi import FastAPI
from fastapi.testclient import TestClient

from app import middleware
from app.config import settings
from tests.helpers import PASSWORD, auth, signup


def test_signing_out_invalidates_the_token_that_was_already_issued(client: TestClient) -> None:
    owner = signup(client)
    token = owner["access_token"]
    assert client.get("/api/auth/me", headers=auth(token)).status_code == 200

    client.post("/api/auth/logout")

    # Clearing the cookie is not the point: the bearer token itself must stop working.
    response = client.get("/api/auth/me", headers=auth(token))
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "session_revoked"


def test_signing_out_stops_the_refresh_cookie_minting_new_tokens(client: TestClient) -> None:
    signup(client)
    assert client.post("/api/auth/refresh").status_code == 200

    client.post("/api/auth/logout")
    client.cookies.clear()

    assert client.post("/api/auth/refresh").status_code == 401


def test_signing_in_again_works_after_signing_out(client: TestClient) -> None:
    owner = signup(client, email="olivia@sparklewash.com")
    client.post("/api/auth/logout")

    response = client.post("/api/auth/login", json={"email": "olivia@sparklewash.com", "password": PASSWORD})

    assert response.status_code == 200
    assert client.get("/api/auth/me", headers=auth(response.json()["access_token"])).status_code == 200
    assert owner["access_token"] != response.json()["access_token"]


def test_repeated_wrong_passwords_lock_the_account_for_a_while(client: TestClient) -> None:
    signup(client, email="olivia@sparklewash.com")
    wrong = {"email": "olivia@sparklewash.com", "password": "not-the-password"}

    for _ in range(settings.max_failed_logins):
        assert client.post("/api/auth/login", json=wrong).status_code == 401

    locked = client.post("/api/auth/login", json=wrong)
    assert locked.status_code == 429
    assert locked.json()["detail"]["code"] == "too_many_attempts"

    # The real password is refused too, otherwise the lock would be trivial to step around.
    right = client.post("/api/auth/login", json={"email": "olivia@sparklewash.com", "password": PASSWORD})
    assert right.status_code == 429


def test_a_good_password_clears_the_failure_count(client: TestClient) -> None:
    signup(client, email="olivia@sparklewash.com")
    wrong = {"email": "olivia@sparklewash.com", "password": "not-the-password"}

    for _ in range(settings.max_failed_logins - 1):
        client.post("/api/auth/login", json=wrong)
    client.post("/api/auth/login", json={"email": "olivia@sparklewash.com", "password": PASSWORD})

    # Without a reset, one more failure would tip an account that just signed in successfully.
    assert client.post("/api/auth/login", json=wrong).status_code == 401


def test_every_response_carries_the_security_headers(client: TestClient) -> None:
    response = client.get("/health")

    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert "geolocation=(self)" in response.headers["Permissions-Policy"]
    assert response.headers["X-Request-ID"]


def test_an_unknown_route_answers_in_the_same_error_shape(client: TestClient) -> None:
    response = client.get("/nope")

    assert response.status_code == 404
    assert response.json()["detail"] == {"code": "not_found", "message": "Not Found"}


def test_a_bad_request_body_names_the_fields(client: TestClient) -> None:
    response = client.post("/api/auth/login", json={"email": "not-an-email"})

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail["code"] == "invalid_request"
    assert set(detail["fields"]) == {"email", "password"}


def test_readiness_checks_the_database(client: TestClient) -> None:
    assert client.get("/health/ready").json() == {"status": "ready"}


def test_even_a_crash_carries_the_request_id_and_the_security_headers() -> None:
    """The 500 handler runs outside the middleware, so its headers have to be set separately.

    This is the response where the id matters most: it is the one the caller is asked to quote.
    """
    app = FastAPI()
    middleware.install(app)

    @app.get("/boom")
    def boom() -> None:
        raise RuntimeError("kaboom")

    with TestClient(app, raise_server_exceptions=False) as crashing:
        response = crashing.get("/boom")

    assert response.status_code == 500
    assert response.headers["X-Request-ID"] == response.json()["detail"]["request_id"]
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
