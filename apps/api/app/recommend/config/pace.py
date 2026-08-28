"""여행 속도별 일정 조립 정책.

문서에 합의한 dict 모양을 유지해 3단계에서 변환 없이 쓴다.
"""

from typing import TypedDict


class PaceRule(TypedDict):
    places_per_day: int
    rest_min: int
    window: tuple[str, str]


PACE: dict[str, PaceRule] = {
    # 장소 수만 줄이면 오후 일찍 일정이 끝난다. 방문 사이 여백도 넓혀
    # 하루 전체를 천천히 쓰는 프리셋으로 만든다.
    "relaxed": {"places_per_day": 3, "rest_min": 110, "window": ("10:00", "19:00")},
    "normal": {"places_per_day": 4, "rest_min": 25, "window": ("09:00", "19:00")},
    "packed": {"places_per_day": 5, "rest_min": 15, "window": ("08:00", "21:00")},
}
