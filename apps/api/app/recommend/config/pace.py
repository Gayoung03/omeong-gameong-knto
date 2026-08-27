"""여행 속도별 일정 조립 정책.

문서에 합의한 dict 모양을 유지해 3단계에서 변환 없이 쓴다.
"""

from typing import TypedDict


class PaceRule(TypedDict):
    places_per_day: int
    rest_min: int
    window: tuple[str, str]


PACE: dict[str, PaceRule] = {
    "relaxed": {"places_per_day": 3, "rest_min": 40, "window": ("10:00", "18:00")},
    "normal": {"places_per_day": 4, "rest_min": 25, "window": ("09:00", "19:00")},
    "packed": {"places_per_day": 5, "rest_min": 15, "window": ("08:00", "21:00")},
}
