from typing import Any

from fastapi.testclient import TestClient

PASSWORD = "password123"


def signup(
    client: TestClient,
    *,
    email: str = "olivia@sparklewash.com",
    business_name: str = "Sparkle Car Wash",
    full_name: str = "Olivia Owner",
    password: str = PASSWORD,
    **extra: Any,
) -> dict[str, Any]:
    response = client.post(
        "/api/auth/signup",
        json={
            "email": email,
            "business_name": business_name,
            "full_name": full_name,
            "password": password,
            **extra,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def invite(
    client: TestClient,
    owner_token: str,
    *,
    email: str = "eli@sparklewash.com",
    full_name: str = "Eli Employee",
    role: str = "employee",
) -> dict[str, Any]:
    response = client.post(
        "/api/team/invites",
        json={"email": email, "full_name": full_name, "role": role},
        headers=auth(owner_token),
    )
    assert response.status_code == 201, response.text
    return response.json()


def invite_token(invite_body: dict[str, Any]) -> str:
    return invite_body["invite_url"].rsplit("/", 1)[-1]


def accept(client: TestClient, raw_token: str, *, full_name: str = "Eli Employee") -> dict[str, Any]:
    response = client.post(
        f"/api/invites/{raw_token}/accept",
        json={"full_name": full_name, "password": PASSWORD},
    )
    assert response.status_code == 200, response.text
    return response.json()


def join(client: TestClient, owner_token: str, *, email: str, role: str, full_name: str) -> dict[str, Any]:
    """Invite someone and accept on their behalf; returns the new member's session payload."""
    body = invite(client, owner_token, email=email, full_name=full_name, role=role)
    return accept(client, invite_token(body), full_name=full_name)


# A point in Sydney, and one about 40 m north of it.
SHOP_LAT = -33.870000
SHOP_LNG = 151.200000
NEAR_SHOP = {"latitude": SHOP_LAT + 0.00036, "longitude": SHOP_LNG, "accuracy_m": 10}
FAR_FROM_SHOP = {"latitude": SHOP_LAT + 0.05, "longitude": SHOP_LNG, "accuracy_m": 10}


def create_zone(
    client: TestClient,
    owner_token: str,
    *,
    name: str = "Harbour St Car Wash",
    latitude: float = SHOP_LAT,
    longitude: float = SHOP_LNG,
    radius_m: int = 150,
) -> dict[str, Any]:
    response = client.post(
        "/api/locations",
        json={"name": name, "latitude": latitude, "longitude": longitude, "radius_m": radius_m},
        headers=auth(owner_token),
    )
    assert response.status_code == 201, response.text
    return response.json()
