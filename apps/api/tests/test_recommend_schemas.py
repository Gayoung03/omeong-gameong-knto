import uuid
from datetime import time

import pytest
from pydantic import ValidationError

from app.recommend.schemas import BusinessHour, Candidate, ScoredCandidate, Weights


def _candidate_data() -> dict:
    return {
        "place_id": uuid.uuid4(),
        "lat": 33.4996,
        "lng": 126.5312,
        "item_type": "attraction",
        "environment": "outdoor",
        "average_stay_minutes": 90,
        "tags": ["바다", "산책"],
        "amenities": ["주차장"],
        "rating_avg": 4.5,
        "saved_count": 12,
        "business_hours": [{"day_of_week": 1, "opens_at": "09:00", "closes_at": "18:00"}],
    }


def test_candidate_contract_accepts_itinerary_fields() -> None:
    candidate = Candidate(**_candidate_data())

    assert candidate.business_hours[0].opens_at == time(9)
    assert candidate.item_type.value == "attraction"


def test_business_hour_requires_complete_time_pair() -> None:
    with pytest.raises(ValidationError, match="함께 설정"):
        BusinessHour(day_of_week=1, opens_at=time(9))


def test_weights_must_sum_to_one() -> None:
    with pytest.raises(ValidationError, match="합은 1"):
        Weights(preference=0.5, pet=0.5, proximity=0.5, rating=0, weather=0, popularity=0)


def test_scored_candidate_requires_all_six_sub_scores() -> None:
    with pytest.raises(ValidationError, match="sub_scores 키"):
        ScoredCandidate(
            **_candidate_data(), total_score=0.8, sub_scores={"pet": 0.8}, reason="안전"
        )
