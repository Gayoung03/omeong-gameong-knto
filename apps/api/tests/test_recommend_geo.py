import pytest

from app.recommend.common.geo import haversine, haversine_m


def test_same_coordinate_distance_is_zero() -> None:
    assert haversine_m((33.4996, 126.5312), (33.4996, 126.5312)) == 0


def test_jeju_to_seogwipo_distance_is_plausible_and_symmetric() -> None:
    jeju = (33.4996, 126.5312)
    seogwipo = (33.2541, 126.5601)

    distance = haversine_m(jeju, seogwipo)
    assert 27_000 < distance < 28_000
    assert haversine_m(seogwipo, jeju) == pytest.approx(distance)
    assert haversine(jeju, seogwipo) == distance


def test_invalid_latitude_is_rejected() -> None:
    with pytest.raises(ValueError, match="위도"):
        haversine_m((91, 126), (33, 126))
