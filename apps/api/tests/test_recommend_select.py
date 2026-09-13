import uuid
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from app.db.models.enums import ScheduleItemType
from app.recommend.itinerary.select import _diversity_group, _overlaps_midday
from app.recommend.schemas import ScoredCandidate

KST = ZoneInfo("Asia/Seoul")


def _candidate(*, source_category=None, tags=None, item_type="attraction") -> ScoredCandidate:
    return ScoredCandidate(
        place_id=uuid.uuid4(),
        lat=33.5,
        lng=126.5,
        item_type=item_type,
        source_category=source_category,
        environment=None,
        average_stay_minutes=60,
        tags=tags or [],
        total_score=0.5,
        sub_scores={
            "preference": 0.5,
            "pet": 0.5,
            "proximity": 0.5,
            "rating": 0.0,
            "weather": 0.5,
            "popularity": 0.0,
        },
        reason="x",
    )


def _at(hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 8, 31, hour, minute, tzinfo=KST)


@pytest.mark.parametrize(
    ("start", "end", "expected"),
    [
        (_at(13), _at(14), True),  # 완전히 안쪽
        (_at(11), _at(12, 30), True),  # 앞 경계와 겹침
        (_at(14, 30), _at(16), True),  # 뒤 경계와 겹침
        (_at(10), _at(12), False),  # 정확히 12:00 에 끝남 → 안 겹침
        (_at(15), _at(16), False),  # 정확히 15:00 에 시작 → 안 겹침
        (_at(9), _at(11), False),  # 오전
    ],
)
def test_overlaps_midday_boundaries(start: datetime, end: datetime, expected: bool) -> None:
    assert _overlaps_midday(start, end) is expected


def test_diversity_group_prefers_source_category() -> None:
    assert _diversity_group(_candidate(source_category="beach")) == "coast"
    assert _diversity_group(_candidate(source_category="cafe")) == "cafe"


@pytest.mark.parametrize(
    ("tags", "expected"),
    [
        (["sea"], "coast"),
        (["walk"], "nature"),
        (["rest"], "nature"),
        (["indoor_tourism"], "culture"),
        (["experience"], "experience"),
    ],
)
def test_diversity_group_falls_back_to_tags(tags: list[str], expected: str) -> None:
    assert _diversity_group(_candidate(tags=tags)) == expected


def test_diversity_group_defaults_to_item_type() -> None:
    group = _diversity_group(_candidate(tags=["unknown"], item_type=ScheduleItemType.CAFE))
    assert group == ScheduleItemType.CAFE.value
