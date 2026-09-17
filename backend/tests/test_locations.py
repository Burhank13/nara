from fastapi.testclient import TestClient

from tests.helpers import SHOP_LAT, SHOP_LNG, auth, create_zone, join, signup


def test_the_owner_creates_a_zone_with_the_default_radius(client: TestClient) -> None:
    owner = signup(client)

    response = client.post(
        "/api/locations",
        json={"name": "Harbour St Car Wash", "latitude": SHOP_LAT, "longitude": SHOP_LNG},
        headers=auth(owner["access_token"]),
    )

    assert response.status_code == 201
    assert response.json()["radius_m"] == 150


def test_a_radius_outside_the_allowed_range_is_refused(client: TestClient) -> None:
    owner = signup(client)

    too_tight = client.post(
        "/api/locations",
        json={"name": "Tight", "latitude": SHOP_LAT, "longitude": SHOP_LNG, "radius_m": 20},
        headers=auth(owner["access_token"]),
    )
    too_wide = client.post(
        "/api/locations",
        json={"name": "Wide", "latitude": SHOP_LAT, "longitude": SHOP_LNG, "radius_m": 900},
        headers=auth(owner["access_token"]),
    )

    assert too_tight.status_code == 422
    assert too_wide.status_code == 422


def test_staff_can_read_the_zones_but_not_change_them(client: TestClient) -> None:
    owner = signup(client)
    create_zone(client, owner["access_token"])
    employee = join(
        client,
        owner["access_token"],
        email="eli@sparklewash.com",
        role="employee",
        full_name="Eli Employee",
    )
    employee_token = employee["access_token"]

    listed = client.get("/api/locations", headers=auth(employee_token))
    created = client.post(
        "/api/locations",
        json={"name": "Sneaky", "latitude": SHOP_LAT, "longitude": SHOP_LNG},
        headers=auth(employee_token),
    )

    assert listed.status_code == 200
    assert [zone["name"] for zone in listed.json()] == ["Harbour St Car Wash"]
    assert created.status_code == 403


def test_a_zone_can_be_moved_and_resized(client: TestClient) -> None:
    owner = signup(client)
    zone = create_zone(client, owner["access_token"])

    response = client.patch(
        f"/api/locations/{zone['id']}",
        json={"radius_m": 250, "name": "Harbour St (rear gate)"},
        headers=auth(owner["access_token"]),
    )

    assert response.status_code == 200
    assert response.json()["radius_m"] == 250
    assert response.json()["name"] == "Harbour St (rear gate)"


def test_a_deleted_zone_disappears_from_the_list(client: TestClient) -> None:
    owner = signup(client)
    zone = create_zone(client, owner["access_token"])

    assert (
        client.delete(f"/api/locations/{zone['id']}", headers=auth(owner["access_token"])).status_code == 204
    )
    assert client.get("/api/locations", headers=auth(owner["access_token"])).json() == []


def test_one_business_never_sees_another_business_zones(client: TestClient) -> None:
    first = signup(client)
    zone = create_zone(client, first["access_token"])
    second = signup(client, email="sam@shinewash.com", business_name="Shine Wash", full_name="Sam Owner")

    listed = client.get("/api/locations", headers=auth(second["access_token"]))
    patched = client.patch(
        f"/api/locations/{zone['id']}", json={"radius_m": 300}, headers=auth(second["access_token"])
    )

    assert listed.json() == []
    assert patched.status_code == 404
