from app.db.models.enums import TripPace
from app.recommend.config.pace import PACE


def test_all_trip_paces_have_itinerary_rules() -> None:
    assert set(PACE) == {pace.value for pace in TripPace}


def test_relaxed_pace_contract() -> None:
    relaxed = PACE[TripPace.RELAXED]

    assert relaxed["places_per_day"] == 3
    assert relaxed["rest_min"] == 40
    assert relaxed["window"] == ("10:00", "18:00")
