from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.business import Business
from tests.helpers import (
    FAR_FROM_SHOP,
    NEAR_SHOP,
    SHOP_LAT,
    SHOP_LNG,
    auth,
    create_zone,
    join,
    signup,
)


def shop_with_employee(client: TestClient) -> tuple[str, str]:
    """Returns (owner_token, employee_token) for a business with one zone set up."""
    owner = signup(client)
    create_zone(client, owner["access_token"])
    employee = join(
        client,
        owner["access_token"],
        email="eli@sparklewash.com",
        role="employee",
        full_name="Eli Employee",
    )
    return owner["access_token"], employee["access_token"]


def test_a_shift_starts_inside_the_zone(client: TestClient) -> None:
    _, employee = shop_with_employee(client)

    response = client.post("/api/shifts/start", json=NEAR_SHOP, headers=auth(employee))

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] == "open"
    assert body["location_name"] == "Harbour St Car Wash"
    assert body["start_distance_m"] < 150
    assert body["ended_at"] is None
    assert body["needs_attention"] is False


def test_a_start_outside_the_zone_is_refused_with_the_distance(client: TestClient) -> None:
    _, employee = shop_with_employee(client)

    response = client.post("/api/shifts/start", json=FAR_FROM_SHOP, headers=auth(employee))

    assert response.status_code == 409
    detail = response.json()["detail"]
    assert detail["code"] == "outside_zone"
    assert detail["distance_m"] > 150
    assert detail["radius_m"] == 150
    assert detail["location_name"] == "Harbour St Car Wash"


def test_a_weak_gps_fix_is_refused(client: TestClient) -> None:
    _, employee = shop_with_employee(client)

    response = client.post("/api/shifts/start", json={**NEAR_SHOP, "accuracy_m": 250}, headers=auth(employee))

    assert response.status_code == 409
    detail = response.json()["detail"]
    assert detail["code"] == "gps_inaccurate"
    assert detail["accuracy_m"] == 250
    assert detail["required_accuracy_m"] == 100


def test_a_second_start_is_refused_while_a_shift_is_open(client: TestClient) -> None:
    _, employee = shop_with_employee(client)
    client.post("/api/shifts/start", json=NEAR_SHOP, headers=auth(employee))

    response = client.post("/api/shifts/start", json=NEAR_SHOP, headers=auth(employee))

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "shift_already_open"


def test_a_business_with_no_zone_cannot_start_shifts(client: TestClient) -> None:
    owner = signup(client)
    employee = join(
        client,
        owner["access_token"],
        email="eli@sparklewash.com",
        role="employee",
        full_name="Eli Employee",
    )

    response = client.post("/api/shifts/start", json=NEAR_SHOP, headers=auth(employee["access_token"]))

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "no_zone_configured"


def test_a_read_only_business_cannot_start_a_shift(client: TestClient, db: Session) -> None:
    _, employee = shop_with_employee(client)
    business = db.execute(select(Business)).scalar_one()
    business.trial_ends_at = datetime.now(UTC) - timedelta(days=1)
    db.commit()

    response = client.post("/api/shifts/start", json=NEAR_SHOP, headers=auth(employee))

    assert response.status_code == 402
    assert response.json()["detail"]["code"] == "billing_inactive"


def test_the_current_shift_is_reported_then_cleared(client: TestClient) -> None:
    _, employee = shop_with_employee(client)

    assert client.get("/api/shifts/current", headers=auth(employee)).json()["shift"] is None

    client.post("/api/shifts/start", json=NEAR_SHOP, headers=auth(employee))
    assert client.get("/api/shifts/current", headers=auth(employee)).json()["shift"]["status"] == "open"

    client.post("/api/shifts/end", json={}, headers=auth(employee))
    assert client.get("/api/shifts/current", headers=auth(employee)).json()["shift"] is None


def test_ending_records_the_location_and_closes_the_shift(client: TestClient) -> None:
    _, employee = shop_with_employee(client)
    client.post("/api/shifts/start", json=NEAR_SHOP, headers=auth(employee))

    response = client.post("/api/shifts/end", json=FAR_FROM_SHOP, headers=auth(employee))

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "closed"
    assert body["ended_at"] is not None
    # Ending off-site is allowed, and how far away it happened is kept on the record.
    assert body["end_distance_m"] > 150


def test_ending_works_without_any_location(client: TestClient) -> None:
    """A denied location permission must never trap someone in an open shift."""
    _, employee = shop_with_employee(client)
    client.post("/api/shifts/start", json=NEAR_SHOP, headers=auth(employee))

    response = client.post("/api/shifts/end", json={}, headers=auth(employee))

    assert response.status_code == 200
    assert response.json()["end_distance_m"] is None


def test_ending_still_works_when_the_business_is_read_only(client: TestClient, db: Session) -> None:
    _, employee = shop_with_employee(client)
    client.post("/api/shifts/start", json=NEAR_SHOP, headers=auth(employee))

    business = db.execute(select(Business)).scalar_one()
    business.trial_ends_at = datetime.now(UTC) - timedelta(days=1)
    db.commit()

    assert client.post("/api/shifts/end", json={}, headers=auth(employee)).status_code == 200


def test_ending_without_an_open_shift_is_refused(client: TestClient) -> None:
    _, employee = shop_with_employee(client)

    response = client.post("/api/shifts/end", json={}, headers=auth(employee))

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "no_open_shift"


def test_a_start_is_matched_to_whichever_site_the_phone_is_at(client: TestClient) -> None:
    owner = signup(client)
    create_zone(client, owner["access_token"], name="Harbour St")
    create_zone(client, owner["access_token"], name="Airport Rd", latitude=SHOP_LAT + 0.5)
    employee = join(
        client,
        owner["access_token"],
        email="eli@sparklewash.com",
        role="employee",
        full_name="Eli Employee",
    )

    response = client.post(
        "/api/shifts/start",
        json={"latitude": SHOP_LAT + 0.5, "longitude": SHOP_LNG, "accuracy_m": 10},
        headers=auth(employee["access_token"]),
    )

    assert response.status_code == 201
    assert response.json()["location_name"] == "Airport Rd"


def test_my_hours_totals_the_period(client: TestClient) -> None:
    _, employee = shop_with_employee(client)
    client.post("/api/shifts/start", json=NEAR_SHOP, headers=auth(employee))
    client.post("/api/shifts/end", json=NEAR_SHOP, headers=auth(employee))

    response = client.get("/api/shifts/mine?period=week", headers=auth(employee))

    assert response.status_code == 200
    body = response.json()
    assert body["period"] == "week"
    assert body["shift_count"] == 1
    assert body["total_hours"] == body["shifts"][0]["hours"]


def test_my_hours_only_shows_my_own_shifts(client: TestClient) -> None:
    owner_token, employee = shop_with_employee(client)
    client.post("/api/shifts/start", json=NEAR_SHOP, headers=auth(employee))

    response = client.get("/api/shifts/mine", headers=auth(owner_token))

    assert response.json()["shift_count"] == 0
