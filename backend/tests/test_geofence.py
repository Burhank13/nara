from app.models.location import Location
from app.services.geofence import check_zones, distance_m

# Sydney Harbour Bridge to the Opera House: about 670 m apart.
BRIDGE = (-33.852222, 151.210556)
OPERA_HOUSE = (-33.856784, 151.215297)
SHOP = (-33.870000, 151.200000)


def zone(name: str, lat: float, lng: float, radius_m: int = 150) -> Location:
    return Location(name=name, latitude=lat, longitude=lng, radius_m=radius_m, is_active=True)


def test_distance_between_two_known_points() -> None:
    measured = distance_m(*BRIDGE, *OPERA_HOUSE)

    assert 650 < measured < 700


def test_distance_to_the_same_point_is_zero() -> None:
    assert distance_m(*SHOP, *SHOP) == 0


def test_a_point_inside_the_radius_is_in_the_zone() -> None:
    # Roughly 40 m north of the shop.
    check = check_zones([zone("Harbour St", *SHOP)], SHOP[0] + 0.00036, SHOP[1])

    assert check is not None
    assert check.inside
    assert 30 < check.distance_m < 50


def test_a_point_outside_the_radius_is_reported_with_its_distance() -> None:
    check = check_zones([zone("Harbour St", *SHOP)], *OPERA_HOUSE)

    assert check is not None
    assert not check.inside
    assert check.distance_m > 150


def test_no_zones_means_no_check() -> None:
    assert check_zones([], *SHOP) is None


def test_the_containing_zone_wins_over_a_closer_one_that_does_not_contain_the_point() -> None:
    # A tight 50 m zone the phone sits just outside, and a wide one it sits inside.
    tight = zone("Tight", SHOP[0] + 0.0007, SHOP[1], radius_m=50)
    wide = zone("Wide", SHOP[0] + 0.0020, SHOP[1], radius_m=300)

    check = check_zones([tight, wide], SHOP[0], SHOP[1])

    assert check is not None
    assert check.location.name == "Wide"
    assert check.inside


def test_the_nearest_zone_is_chosen_when_several_contain_the_point() -> None:
    near = zone("Near", SHOP[0] + 0.0003, SHOP[1], radius_m=300)
    far = zone("Far", SHOP[0] + 0.0020, SHOP[1], radius_m=300)

    check = check_zones([far, near], SHOP[0], SHOP[1])

    assert check is not None
    assert check.location.name == "Near"
